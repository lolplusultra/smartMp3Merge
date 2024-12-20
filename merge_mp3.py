import os
import re
from pydub import AudioSegment
from collections import defaultdict
from difflib import SequenceMatcher

# Dictionary for transliteration of special characters to ASCII equivalents
SPECIAL_CHAR_MAP = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "ß": "ss",
    "Ä": "Ae",
    "Ö": "Oe",
    "Ü": "Ue",
    "é": "e",
    "è": "e",
    "ê": "e",
    "à": "a",
    "á": "a",
    "â": "a",
    "ç": "c",
    "ñ": "n"
    # Add more mappings as needed
}

# Global counter for Folge numbers
folge_counter = 1

def replace_special_characters(text):
    """
    Replace special characters in the text using the SPECIAL_CHAR_MAP.
    """
    for char, replacement in SPECIAL_CHAR_MAP.items():
        text = text.replace(char, replacement)
    return text

def extract_kapitel_or_teil_number(filename):
    """
    Extracts the Kapitel or Teil number from the filename.
    If neither is found, return 0.
    """
    kapitel_match = re.search(r"(Kapitel|Teil)\s*(\d+)", filename)
    return int(kapitel_match.group(2)) if kapitel_match else 0

def extract_title(filename):
    """
    Extract the title from the filename (before any number or extension).
    """
    # Assuming the title is everything before a number or file extension
    match = re.match(r"([a-zA-Z0-9\s]+)(\d+|\.mp3|\.mp4|\.pdf)?$", filename)
    return match.group(1) if match else filename

def similar(a, b):
    """
    Function to calculate similarity ratio between two strings.
    """
    return SequenceMatcher(None, a, b).ratio()

def merge_mp3_files(mp3_files, output_file):
    """
    Merges multiple MP3 files into a single MP3 file.
    """
    # Load the first file
    combined = AudioSegment.from_mp3(mp3_files[0])

    # Append the rest of the files
    for mp3 in mp3_files[1:]:
        next_audio = AudioSegment.from_mp3(mp3)
        combined += next_audio

    # Export the combined audio to a new MP3 file
    combined.export(output_file, format="mp3")
    print(f"Merged audio saved as {output_file}")

def clean_file_name(filename):
    """
    Cleans the filename to match the desired format.
    If the Folge number starts with '000', it will increment.
    """
    global folge_counter

    # Extract "Folge <number>" regardless of position
    folge_match = re.search(r"Folge\s*(\d+)", filename)
    folge_number = folge_match.group(1) if folge_match else "000"

    # If the Folge number is "000", increment the counter for each new file processed
    if folge_number == "000":
        folge_number = str(folge_counter).zfill(3)
        folge_counter += 1
    else:
        # Ensure the Folge number is always 3 digits
        folge_number = folge_number.zfill(3)

    # Remove "Folge <number>" and any content inside parentheses/brackets
    filename = re.sub(r"Folge\s*\d+|\s*\(.*?\)|\s*\[.*?\]", "", filename)
    
    # Remove common prefixes like "Kapitel" and "Teil"
    filename = re.sub(r"(Kapitel|Teil)\s*\d+", "", filename)
    
    # Replace spaces with underscores
    filename = filename.replace(" ", "_")
    
    # Replace special characters with safe equivalents
    filename = replace_special_characters(filename)
    
    # Remove any double underscores
    filename = re.sub(r"-+", "_", filename)
    filename = re.sub(r"_+", "_", filename)
    
    # Strip leading/trailing underscores
    filename = filename.strip("_")
    
    # Add the extracted "Folge" number to the beginning
    cleaned = f"{folge_number}_{filename}"
    
    return cleaned

def group_files_by_similarity(directory, similarity_threshold=0.9):
    """
    Groups files by their title similarity.
    """
    groups = defaultdict(list)
    
    # Traverse through the folder and classify files
    for filename in os.listdir(directory):
        if filename.endswith(".mp3"):
            title = extract_title(filename)
            added = False
            
            # Check against existing groups
            for group_title in list(groups.keys()):
                if similar(title, group_title) > similarity_threshold:
                    groups[group_title].append(os.path.join(directory, filename))
                    added = True
                    break
            
            # If not added to any group, create a new group
            if not added:
                groups[title].append(os.path.join(directory, filename))
    
    return groups

def merge_files_in_directory(directory):
    """
    Merge files in the directory by similarity in title.
    """
    file_groups = group_files_by_similarity(directory)
    
    # For each group of files with similar titles, merge them
    for group_title, files in file_groups.items():

        # Extract Kapitel or Teil numbers and sort files accordingly
        files_with_kapitel_or_teil = [(extract_kapitel_or_teil_number(os.path.basename(f)), f) for f in files]
        
        # Remove duplicates by using a set to avoid double counting of the same Kapitel/Teil
        seen = set()
        unique_files = []
        for number, file in files_with_kapitel_or_teil:
            if number not in seen:
                unique_files.append((number, file))
                seen.add(number)
        
        unique_files.sort()  # Sort by Kapitel/Teil number
        kapitel_or_teil_numbers = [entry[0] for entry in unique_files]
        
        # Check for start with 1
        if kapitel_or_teil_numbers[0] != 1:
            print(f"Warning: Group '{group_title}' has no start.")
            continue

        # Check for too few files
        if len(kapitel_or_teil_numbers) <= 1:
            print(f"Warning: Group '{group_title}' has only one Kapitel/Teil.")
            continue

        # Check for gaps in Kapitel/Teil numbers
        gap_detected = False
        for i in range(1, len(kapitel_or_teil_numbers)):
            if kapitel_or_teil_numbers[i] != kapitel_or_teil_numbers[i-1] + 1:
                gap_detected = True
        if gap_detected:
            print(f"Warning: Gap detected in Kapitel/Teil order for group '{group_title}'.")
            continue
        
        # Get the name of the first file (base name without directory)
        first_file_name = os.path.basename(unique_files[0][1])
        first_file_name_without_extension = os.path.splitext(first_file_name)[0]
        
        # Clean the name to match the desired format
        cleaned_name = clean_file_name(first_file_name_without_extension)
        
        # Construct the output file name
        output_file = os.path.join(directory, f"{cleaned_name}.mp3")
        
        # Merge files in the sorted order
        sorted_files = [f[1] for f in unique_files]
        merge_mp3_files(sorted_files, output_file)

# Prompt the user for the directory containing MP3 files
directory = input("Enter the folder path containing MP3 files: ").strip()

# Check if the directory exists
if not os.path.isdir(directory):
    print("Error: The specified folder does not exist.")
else:
    # Call the function to merge files
    merge_files_in_directory(directory)
