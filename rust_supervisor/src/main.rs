// main.rs
//
// A supervisor process for the C++ pipeline. It starts sdr_platform as a
// child process, waits for it to finish, and restarts it if it exits with
// an error or is killed, up to a maximum number of restarts.
//
// It also occasionally kills the child process on purpose (failure
// injection) to confirm that the restart logic actually works.

use rand::Rng;
use std::time::Duration;
use tokio::process::Command;
use tokio::time::sleep;

const MAX_RESTARTS: u32 = 5;
const RESTART_DELAY: Duration = Duration::from_secs(1);
const FAILURE_INJECTION_CHANCE_PERCENT: u32 = 30;

#[tokio::main]
async fn main() {
    // Every argument after the supervisor's own program name is passed
    // straight through to the C++ program.
    let child_args: Vec<String> = std::env::args().skip(1).collect();
    let child_args = if child_args.is_empty() {
        vec!["live".to_string()]
    } else {
        child_args
    };

    println!("SDR Supervisor starting.");
    println!("Running the C++ pipeline with args {child_args:?}, restarting on failure.");
    println!("Max restarts: {MAX_RESTARTS}\n");

    let mut restart_count = 0;

    loop {
        println!("Run attempt {}", restart_count + 1);

        let outcome = run_child_with_failure_injection(&child_args).await;

        match outcome {
            RunOutcome::ExitedCleanly => {
                println!("Child process exited normally. Supervisor is done.\n");
                break;
            }
            RunOutcome::Crashed(code) => {
                println!("Child process exited with a non-zero code: {code}");
            }
            RunOutcome::KilledBySupervisor => {
                println!("Supervisor intentionally killed the child (failure injection test).");
            }
            RunOutcome::FailedToStart(err) => {
                println!("Could not start the child process: {err}");
                println!("Check that `cmake --build .` has been run inside the build folder.");
                break;
            }
        }

        restart_count += 1;
        if restart_count >= MAX_RESTARTS {
            println!("Reached the maximum number of restarts ({MAX_RESTARTS}). Giving up.");
            break;
        }

        println!("Restarting in {:?}.\n", RESTART_DELAY);
        sleep(RESTART_DELAY).await;
    }

    println!("SDR Supervisor finished after {} attempt(s).", restart_count + 1);
}

enum RunOutcome {
    ExitedCleanly,
    Crashed(i32),
    KilledBySupervisor,
    FailedToStart(std::io::Error),
}

// Starts the C++ program and waits for it to finish. Sometimes kills it
// early on purpose, to test the restart logic under a failure condition.
async fn run_child_with_failure_injection(child_args: &[String]) -> RunOutcome {
    let child_path = "../build/sdr_platform";

    let mut child = match Command::new(child_path).args(child_args).spawn() {
        Ok(child) => child,
        Err(err) => return RunOutcome::FailedToStart(err),
    };

    let should_inject_failure = {
        let mut rng = rand::thread_rng();
        rng.gen_range(0..100) < FAILURE_INJECTION_CHANCE_PERCENT
    };

    if should_inject_failure {
        let kill_after = Duration::from_millis(rand::thread_rng().gen_range(50..300));

        tokio::select! {
            status = child.wait() => {
                return status_to_outcome(status);
            }
            _ = sleep(kill_after) => {
                println!("Injecting a simulated failure: killing the child process now.");
                let _ = child.kill().await;
                let _ = child.wait().await;
                return RunOutcome::KilledBySupervisor;
            }
        }
    }

    let status = child.wait().await;
    status_to_outcome(status)
}

fn status_to_outcome(status: std::io::Result<std::process::ExitStatus>) -> RunOutcome {
    match status {
        Ok(exit_status) if exit_status.success() => RunOutcome::ExitedCleanly,
        Ok(exit_status) => RunOutcome::Crashed(exit_status.code().unwrap_or(-1)),
        Err(err) => RunOutcome::FailedToStart(err),
    }
}
