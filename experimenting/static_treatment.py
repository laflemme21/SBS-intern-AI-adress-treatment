import re
from typing import Any
import json
from asynchronus_requests import extract_from_excel_and_build_prompt
import pandas as pd

def has_n_or_less(item: Any, n: int) -> bool:
    """
    Return True if the input contains n counted words or fewer, False otherwise.
    Counting rules:
    - Count all numbers (e.g., 12, 12-14, 75001, 12B).
    - Do not count words containing fewer than 2 letters.
    """
    if item is None:
        return False
    text = str(item).strip()
    if not text:
        return True

    tokens = re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)

    def counts_as_word(tok: str) -> bool:
        # Numbers or number ranges like 12, 12-14, 12/14
        if re.fullmatch(r"\d+(?:[-/]\d+)*", tok):
            return True
        # Numbers with a single letter suffix like 12B
        if re.fullmatch(r"\d+[A-Za-z]", tok):
            return True
        # Count only tokens with at least 2 letters
        letters = re.findall(r"[^\W\d_]", tok, flags=re.UNICODE)
        return len(letters) >= 2

    count = sum(1 for t in tokens if counts_as_word(t))
    return count <= n

def contains_any_word(list1: list[str], list2: list[str]) -> str | None:
    """
    Return the first string in list1 that contains any word matching any item in list2 (case-insensitive).
    Each element in list1 is split into words; each word is compared to each item in list2 as a whole string.
    If a match is found, return the string from list1; else return None.
    """
    if not list1 or not list2:
        return None
    target_set = set(item.lower() for item in list2 if isinstance(item, str))
    for item in list1:
        if isinstance(item, str):
            words = re.findall(r"\b[\w'-]+\b", item, flags=re.UNICODE)
            for w in words:
                if w.lower() in target_set:
                    return item
    return None

def count_empty_strings(lst: list[str]) -> int:
    """
    Return the number of empty strings ("") in the given list.
    """
    return sum(1 for item in lst if pd.isna(item) or (isinstance(item, str) and item.strip() == ""))

def main():

    
    with open('common_words.json', 'r', encoding='utf-8') as f:
        keys = json.load(f)

    att_mots_cles = keys["att_of_list"]

    addresses, contexts, df = extract_from_excel_and_build_prompt("Adresses_test.xlsx", "prompt_template.txt", n_rows=1900, build_prompt=False)
    # keep only columns 3,4,5,6 and 11
    df = df.iloc[:, [3, 4, 5, 6, 11]]
    df = df.values.tolist()
    total_addresses = len(df)
    len_addresses = len(df)
    i = 0
    only_road = 0
    road_and_co = 0
    while i < len_addresses:
        df[i].append(count_empty_strings(df[i]))
        if df[i][-1] >= 3 and has_n_or_less(df[i][-2], 3):
            df.pop(i)
            len_addresses -= 1
            only_road += 1
            if i<20:
                print(i)
        elif df[i][-1] >= 2 and has_n_or_less(contains_any_word(df[i][0:4], att_mots_cles), 4):
            # print(f"Address {i} contains keywords: {df[i]}")
            df.pop(i)
            len_addresses -= 1
            road_and_co += 1
            if i<20:
                print(i)
        else:
            i += 1

    print(f"Num of addresses with 3 words or less: {only_road} out of {total_addresses}, {only_road / total_addresses if total_addresses else 0:.2f}")
    print(f"Num of addresses with 2 empty strings or more and keywords: {road_and_co} out of {total_addresses}, {road_and_co / total_addresses if total_addresses else 0:.2f}")
    print(f"Total Ratio: {(total_addresses - len(df)) / total_addresses if total_addresses else 0:.2f}")

main()