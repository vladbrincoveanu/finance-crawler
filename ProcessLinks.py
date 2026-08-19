"""
Removes all of the duplicate links from the idea_links.txt file.
Then saves the new list to a new file called idea_links_no_duplicates.txt
"""
import glob
import os


def remove_duplicates():
    # get all of the files in the current dir that start with idea_links
    files = glob.glob('idea_links*.txt')
    # Keep deterministic ordering so weekly limited crawls are predictable.
    files = sorted(
        (filename for filename in files if filename != 'idea_links_no_duplicates.txt'),
        key=os.path.getmtime,
    )
    all_ideas = []
    seen = set()
    for filename in files:
        with open(filename, 'r') as f:
            idea_links = f.readlines()
        idea_links = [link.strip() for link in idea_links]
        # remove any text at the end of any string starting with /messages
        idea_links = [link.split('/messages')[0] for link in idea_links]
        for link in idea_links:
            if link and link not in seen:
                seen.add(link)
                all_ideas.append(link)
    with open('idea_links_no_duplicates.txt', 'w') as f:
        for link in all_ideas:
            f.write(link + '\n')


if __name__ == '__main__':
    remove_duplicates()
