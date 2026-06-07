import re

flight_string = "ABD4801"

# Extract letters and numbers separately
letters = re.findall(r'[A-Za-z]+', flight_string)[0]
numbers = re.findall(r'\d+', flight_string)[0]

print(f"Airline Code: {letters}")  # Output: ABD
print(f"Flight Number: {numbers}")  # Output: 4801