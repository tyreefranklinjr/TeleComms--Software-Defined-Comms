import random

def introduce_noise(modulated_data: list, error_probability: float = 0.05) -> list:
    """
    Takes a list of modulated floats and randomly flips a percentage 
    of them based on the provided error probability (e.g., 0.05 for 5%).
    """
    noisy_data = []
    for val in modulated_data:
       
        if random.random() < error_probability:
            noisy_data.append(-val)
        else:
            noisy_data.append(val)
            
    return noisy_data