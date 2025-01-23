from PyPDF2 import PdfReader, PdfWriter

import os
import json

def getBookmarksPageNumbers(pdf):
    bookmarks = []
    def reviewBookmarks(bookmarks_list, indent=0):
        for b in bookmarks_list:
            if isinstance(b, list):
                reviewBookmarks(b, indent + 4)
            else:
                pg_num = pdf.get_destination_page_number(b) + 1  # page count starts from 0
                bookmarks.append((indent, b.title, pg_num))

    reviewBookmarks(pdf.outline)
    return bookmarks

def initialize_bookmarks(pdf_path, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
        print(f"Removed outdated bookmarks file at {filepath}")
    
    print(f"Generating new bookmarks at {filepath}...")

    bookmarks = []
    page_length = 0
    
    with open(pdf_path, "rb") as f:
        pdf = PdfReader(f)
        bookmarks = getBookmarksPageNumbers(pdf)
        page_length = len(pdf.pages)

    # print(bookmarks)

    pages = []
    bookmarks_json = {}

    current_chap = 0
    section_pages = []

    for b in bookmarks:
        if b[0] == 0: # where a chapter starts
            if section_pages != []:
                bookmarks_json[f"Chapter {current_chap} sections"] = {}
                for idx in range(len(section_pages)):
                    if idx+1 == len(section_pages):
                        bookmarks_json[f"Chapter {current_chap} sections"][section_pages[idx][0]] = (section_pages[idx][1], b[2])
                    else:
                        bookmarks_json[f"Chapter {current_chap} sections"][section_pages[idx][0]] = (section_pages[idx][1], section_pages[idx+1][1])
                
            section_pages = []

            if any(char.isdigit() for char in b[1]): # skips over non-chapter
                current_chap += 1

            pages.append((b[1],b[2]))
            
        else: # where a section starts
            section_pages.append((b[1],b[2]))

    bookmarks_json["page_ranges"] = {}
    for idx in range(len(pages)):
        if idx+1 == len(pages):
            bookmarks_json["page_ranges"][pages[idx][0]] = (pages[idx][1], page_length)
        else:
            bookmarks_json["page_ranges"][pages[idx][0]] = (pages[idx][1], pages[idx+1][1])
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(bookmarks_json, f, ensure_ascii=False, indent=4)
        print(f"Bookmarks saved to {filepath}")

    return None

def get_page_ranges(filepath):
    data = json.loads(open(filepath).read())
    page_data = data["page_ranges"]

    chapter_page_ranges  = [
        (value[0], value[1]) for key, value in page_data.items() if key.startswith("Chapter")
    ]

    return chapter_page_ranges

# initialize_bookmarks("../data/wholeTextbookPsych.pdf", "../data/page_ranges.json")
# print(get_page_ranges("../data/page_ranges.json"))