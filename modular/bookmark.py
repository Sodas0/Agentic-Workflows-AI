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

    pages = []
    bookmarks_json = {}

    current_chap = 0
    current_chap_sections = None

    for b in bookmarks:
        if b[0] == 0:
            # Check if this is a chapter (title starts with "Chapter" and contains a number)
            if b[1].startswith("Chapter") and any(char.isdigit() for char in b[1]):
                if current_chap_sections is not None:
                    bookmarks_json[f"Chapter {current_chap} sections"] = {}
                    for idx in range(len(current_chap_sections)):
                        if idx + 1 == len(current_chap_sections):
                            bookmarks_json[f"Chapter {current_chap} sections"][current_chap_sections[idx][0]] = (
                                current_chap_sections[idx][1], b[2]
                            )
                        else:
                            bookmarks_json[f"Chapter {current_chap} sections"][current_chap_sections[idx][0]] = (
                                current_chap_sections[idx][1], current_chap_sections[idx + 1][1]
                            )

                # Start a new chapter
                current_chap += 1
                current_chap_sections = []
                pages.append((b[1], b[2]))
            else:
                pages.append((b[1], b[2]))
                continue

        else:  # Section starts
            if current_chap_sections is not None:
                current_chap_sections.append((b[1], b[2]))

    # Finalize the last chapter's sections (if any)
    if current_chap_sections is not None:
        bookmarks_json[f"Chapter {current_chap} sections"] = {}
        for idx in range(len(current_chap_sections)):
            if idx + 1 == len(current_chap_sections):
                bookmarks_json[f"Chapter {current_chap} sections"][current_chap_sections[idx][0]] = (
                    current_chap_sections[idx][1], page_length
                )
            else:
                bookmarks_json[f"Chapter {current_chap} sections"][current_chap_sections[idx][0]] = (
                    current_chap_sections[idx][1], current_chap_sections[idx + 1][1]
                )

    bookmarks_json["page_ranges"] = {}
    for idx in range(len(pages)):
        if idx + 1 == len(pages):
            bookmarks_json["page_ranges"][pages[idx][0]] = (pages[idx][1], page_length)
        else:
            bookmarks_json["page_ranges"][pages[idx][0]] = (pages[idx][1], pages[idx + 1][1])
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(bookmarks_json, f, ensure_ascii=False, indent=4)
        print(f"Bookmarks saved to {filepath}")

def get_page_ranges(filepath):
    if not os.path.exists(filepath):
        print(f"No page ranges found at {filepath}")
        return None
    
    data = json.loads(open(filepath).read())
    page_data = data["page_ranges"]

    chapter_page_ranges  = [
        (value[0], value[1]) for key, value in page_data.items() if key.startswith("Chapter")
    ]

    return chapter_page_ranges

def get_breakpoints(filepath, requirements={
    "exact_matches": ["Introduction"],
    "digit_check": True,
}
):
    def valid_key(key, requirements):
        if key in requirements["exact_matches"] or key[0].isdigit() and requirements["digit_check"]:
            return True
        return False

    breakpoints = {}

    if not os.path.exists(filepath):
        print(f"No page ranges found at {filepath}")
        return None
    
    json_page_ranges = None
    with open(filepath, "r", encoding="utf-8") as f:
        print(f"Loading page ranges from {filepath}")
        json_page_ranges = json.load(f)

    i = 1
    chap_str = f"Chapter {i} sections"
    while chap_str in json_page_ranges:
        bp = [
            value[1] for key, value in json_page_ranges[chap_str].items() if valid_key(key, requirements)
        ]

        # print([key for key, value in json_page_ranges[chap_str].items() if valid_key(key, requirements)])

        breakpoints[f"Chapter {i}"] = bp
        i += 1
        chap_str = f"Chapter {i} sections"

    print("Breakpoints loaded")

    return breakpoints

# initialize_bookmarks("../data/wholeTextbookPsych.pdf", "../data/page_ranges.json")
# print(get_page_ranges("../data/page_ranges.json"))
# print(get_breakpoints("../data/page_ranges.json"))