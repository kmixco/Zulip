import itertools
import json
import random
import os
from typing import List, Dict, Any, Text, Optional

def loadConfig():
    # type: () -> Dict [str, Any]
    infile = open("zerver/lib/config.generate_data.json", "r")
    config = json.loads(infile.read())

    return config


def getStreamTitle(gens):
    # type: (Dict[str, Any]) -> str

    # the secret to generating unique data is:
    # make sure that count of each list is a different prime number
    # with these four, we will get 15015 unique values before a dupe
    # 15 * 11 * 7 * 5 * 3 = 15015

    return next(gens["adjectives"]) + " " + next(gens["nouns"]) + " " + \
        next(gens["connectors"]) + " " + next(gens["verbs"]) + " " + \
        next(gens["adverbs"])


def loadGenerators(config):
    # type: (Dict[str, Any]) -> Dict[str, Any]

    results = {}
    cfg = config["gen_fodder"]

    results["nouns"] = itertools.cycle(cfg["nouns"])             # 13 items
    results["adjectives"] = itertools.cycle(cfg["adjectives"])   # 11 items
    results["connectors"] = itertools.cycle(cfg["connectors"])   # 7 items
    results["verbs"] = itertools.cycle(cfg["verbs"])             # 5 items
    results["adverbs"] = itertools.cycle(cfg["adverbs"])         # 3 items
    results["emojis"] = itertools.cycle(cfg["emoji"])
    results["links"] = itertools.cycle(cfg["links"])

    results["maths"] = itertools.cycle(cfg["maths"])
    results["inline-code"] = itertools.cycle(cfg["inline-code"])
    results["code-blocks"] = itertools.cycle(cfg["code-blocks"])
    results["quote-blocks"] = itertools.cycle(cfg["quote-blocks"])

    results["lists"] = itertools.cycle(cfg["lists"])

    return results


def checkForDupes(gens):
    # type: (Dict[str, Any]) -> None

    results = [] # type: List[str]

    for i in range(106):
        key = next(gens["verbs"]) + " " + next(gens["connectors"]) + \
                " " + next(gens["adverbs"])
        if key not in results:
            results.append(key)
            print(key)
        else:
            print("*******\nDupe found at {}\n{}".format(str(i), key))
            break


def parseFile(config, gens, corpus_file):
    # type: (Dict[str, Any], Dict[str, Any], str) -> List[str]

    # let's load the entire file into a dictionary first,
    # then we'll apply our custom filters to it as needed

    paragraphs = [] # type: List[str]

    with open(corpus_file, "r") as infile:
        # OUR DATA: we need to seperate the person talking and what they say
        paragraphs = removeLineBreaks(infile)
        paragraphs = processDialog(paragraphs)
        paragraphs = addFlair(paragraphs, gens)

    return paragraphs


def getFlairGen(length):
    # type: (int) -> List[str]

    # grab the percentages from the config file
    # create a list that we can consume that will guarantee distrubition
    result = []

    for k, v in config["dist_percentages"].items():
        result.extend([k] * (v * length / 100))

    result.extend(["None"] * (length - len(result)))

    random.shuffle(result)
    return result


def addFlair(paragraphs, gens):
    # type: (List[str], Dict[str, Any]) -> List[str]

    # roll the dice and see what kind of flair we should add, if any
    results = []

    flair = getFlairGen(len(paragraphs))

    for i in range(len(paragraphs)):
        key = flair[i]
        if key == "None":
            txt = paragraphs[i]
        elif key == "italic":
            txt = addMD("*", paragraphs[i])
        elif key == "bold":
            txt = addMD("**", paragraphs[i])
        elif key == "strike-thru":
            txt = addMD("~~", paragraphs[i])
        elif key == "quoted":
            txt = ">" + paragraphs[i]
        elif key == "quote-block":
            txt = paragraphs[i] + "\n" + next(gens["quote-blocks"])
        elif key == "inline-code":
            txt = paragraphs[i] + "\n" + next(gens["inline-code"])
        elif key == "code-block":
            txt = paragraphs[i] + "\n" + next(gens["code-blocks"])
        elif key == "math":
            txt = paragraphs[i] + "\n" + next(gens["maths"])
        elif key == "list":
            txt = paragraphs[i] + "\n" + next(gens["lists"])
        elif key == "emoji":
            txt = addEmoji(paragraphs[i], next(gens["emojis"]))
        elif key == "link":
            txt = addLink(paragraphs[i], next(gens["links"]))
        elif key == "picture":
            txt = txt      # todo: implement pictures

        results.append(txt)

    return results


def addMD(mode, text):
    # type: (str, str) -> str

    # mode means: bold, italic, etc.
    # to add a list at the end of a paragraph, * iterm one\n * item two

    # find out how long the line is, then insert the mode before the end

    vals = text.split()
    start = random.randrange(len(vals))
    end = random.randrange(len(vals) - start) + start
    vals[start] = mode + vals[start]
    vals[end] = vals[end] + mode

    return "".join(vals).strip()


def addEmoji(text, emoji):
    # type: (str, str) -> str

    vals = text.split()
    start = random.randrange(len(vals))

    vals[start] = vals[start] + " " + emoji + " "
    return " ".join(vals)


def addLink(text, link):
    # type: (str, str) -> str

    vals = text.split()
    start = random.randrange(len(vals))

    vals[start] = vals[start] + " " + link + " "

    return " ".join(vals)

def removeActions(line):
    # type: (str) -> str

    # sure, we can regex, but why hassle with that?
    newVal = line
    if "[" in line:
        posOne = line.index("[")
        posTwo = line.index("]")

        if posTwo < len(line):
            newVal = line[:posOne] + line[posTwo + 1:]
        else:
            newVal = line[:posOne]

    if newVal != line:
        newVal = removeActions(newVal)

    return newVal


def processDialog(paragraphs):
    # type: (List[str]) -> List[str]

    results = []
    for dialog in paragraphs:
        tup_result = getDialog(dialog)
        if tup_result is not None:
            if tup_result[0] is not None:
                results.append(tup_result)

    return results


def removeLineBreaks(fh):
    # type: (Any) -> List[str]

    # we're going to remove line breaks from paragraphs
    results = []    # save the dialogs as tuples with (author, dialog)

    para = []   # we'll store the lines here to form a paragraph

    for line in fh:
        text = line.strip()
        # this is the standard notification to mark the end of Gutenberg stuff
        if text.startswith("***END OF THE PROJECT GUTENBERG"):
            break

        if text != "":
            para.append(text)
        else:
            if para is not None:
                results.append(" ".join(para))
            # reset the paragraph
            para = []

    return results


def getDialog(line):
    # type: (str) -> Any

    # we've got a line from the play,
    # let's see if it's a line or dialog or something else

    actor = ""
    if '.' in line:
        strpos = line.index('.')
        if strpos > 0:
            actor = line[:strpos]
            vals = actor.split()
            if len(vals) < 2:
                return removeActions(line[strpos + 2:].strip())
            else:
                # no actor, so not a line of dialog
                return None


def writeFile(paragraphs, filename):
    # type: (List[str], str) -> None

    with open(filename, "w") as outfile:
        outfile.write(json.dumps(paragraphs))



def create_test_data():
    # type: () -> None

    gens = loadGenerators(config)   # returns a dictionary of generators

    paragraphs = parseFile(config, gens, config["corpus"]["filename"])

    writeFile(paragraphs, "var/test_messages.json")



config = loadConfig() # type: Dict[str, Any]

if __name__ == "__main__":
    create_test_data() # type: () -> ()

