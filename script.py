import re
import pyperclip
import time

def extract_and_copy(mcq_text):
    # Regex to extract question and options
    question_match = re.search(r'(.+?\?)', mcq_text)  # Capture everything until the first '?'
    options = re.findall(r'([A-D]\) .+?)(?=\s[A-D]\)|$)', mcq_text)  # Capture A) B) C) D) options

    if not question_match or not options:
        print("Invalid format! Make sure there's a '?' and options start with A), B), etc.")
        return

    question = question_match.group(1)
    elements = [question] + options  # First question, then options

    for item in elements:
        pyperclip.copy(item)
        print(f"Copied: {item}")
        time.sleep(5)  # Wait before copying the next item

# Example usage
mcq_text = "How does SQL Injection affect security? A) It allows attackers to insert malicious code into website forms to access databases B) It makes your internet connection unstable C) It drains your device's battery faster D) It causes your screen to display upside down"
extract_and_copy(mcq_text)