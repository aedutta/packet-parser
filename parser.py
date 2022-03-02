import json
import os
import regex
import time
import math

has_category_tags = False

input_directory = 'packets/'
output_directory = 'output/'
os.mkdir(output_directory)


with open('subcat_conversion.json') as f:
    subcat_conversion = json.load(f)

with open('subcat.json') as f:
    subcat = json.load(f)

with open('stop_words.txt') as f:
    stop_words = set(f.readlines())
    stop_words = set([word.strip() for word in stop_words])

num_tossups = 0
num_bonuses = 0
all_questions = []
for (dirpath, dirnames, filenames) in os.walk('packets_classify'):
    for filename in filenames:
        if filename == '.DS_Store':
            continue

        f = open(dirpath + '/' + filename)

        try:
            data = json.load(f)
        except:
            print(dirpath + '/' + filename)
            continue

        all_questions.append(data)
        if 'tossups' in data:
            num_tossups += len(data['tossups'])
        if 'bonuses' in data:
            num_bonuses += len(data['bonuses'])

print(num_tossups)
print(num_bonuses)

def removePunctuation(s, punctuation='''.,!-;:'"\/?@#$%^&*_~'''):
    return ''.join(ch for ch in s if ch not in punctuation)


def get_subcategory(s):
    for key in subcat_conversion:
        works = True
        for word in key.split():
            if word not in s:
                works = False
                break
        if works:
            return subcat_conversion[key]

    return ''


def difference(text1, text2):
    """
    Returns the number of words in common between the two words
    """
    count = 0

    words1 = text1
    words2 = text2
    for word in words1:
        # skip small common words
        # if len(word) < 5: continue
        if word in words2: count += len(word)

    return count


def classify_question(text, is_tossup):
    i = 0
    text = set(text.split())
    text = set([removePunctuation(word).lower() for word in text])
    text = set([word for word in text if word not in stop_words])

    idfs = {word: 0 for word in text}

    best_question = {}
    best_overall_score = 0
    for data in all_questions:
        if is_tossup:
            if len(data['tossups']) == 0: continue
            for word in text:
                for tossup in data['tossups']:
                    if word in tossup['question']:
                        idfs[word] += 1

        elif 'bonuses' in data:
            if len(data['bonuses']) == 0: continue

            for word in text:
                for bonus in data['bonuses']:
                    if word in bonus['leadin']:
                        idfs[word] += 1
    
    if is_tossup:
        for word in idfs:
            idfs[word] = 0 if idfs[word] == 0 else math.log(num_tossups / idfs[word])
    else:
        for word in idfs:
            idfs[word] = 0 if idfs[word] == 0 else math.log(num_bonuses / idfs[word])
    
    for data in all_questions:
        if is_tossup:
            best_score = 0
            best_tu = {}
            if len(data['tossups']) == 0: continue
            for tossup in data['tossups']:
                if 'subcategory' not in tossup:
                    continue
                score = 0
                for word in tossup['question']:
                    if word in idfs:
                        score += idfs[word]
                
                if score > best_score:
                    best_score = score
                    best_tu = tossup

            if best_score > best_overall_score:
                best_question = best_tu
                best_overall_score = best_score

        elif 'bonuses' in data:
            if len(data['bonuses']) == 0: continue

            best_score = 0
            best_bonus = {}
            for bonus in data['bonuses']:
                if 'subcategory' not in bonus:
                    continue
                score = 0
                for word in bonus['leadin']:
                    if word in idfs:
                        score += idfs[word]
                
                if score > best_score:
                    best_score = score
                    best_bonus = bonus
            
            if best_score > best_overall_score:
                best_question = best_bonus
                best_overall_score = best_score

    return best_question['category'], best_question['subcategory'], best_question


for file in os.listdir(input_directory):
    if file == '.DS_Store': continue
    print(file)

    f = open(input_directory + file)
    g = open(output_directory + file[:-4] + '.json', 'w')

    data = {
        "tossups": [],
        "bonuses": []
    }

    packet_text = ''
    for line in f.readlines():
        packet_text += line

    packet_text = packet_text.replace('\n', ' ')
    packet_text = packet_text.replace('', ' ')
    tossups, bonuses = regex.split('bonuses', packet_text, flags=regex.IGNORECASE)
    # tossups, bonuses = regex.split('[Bb][Oo][Nn][Uu][Ss][Ee][Ss]', packet_text)[0], ''

    if has_category_tags:
        bonuses = '>' + bonuses
    else:
        tossups += ' 21.'
        bonuses += ' [10]'

    for i in regex.findall(r'(?<=\d{1,2}\. +|TB\. +|Tiebreaker\. +).+?(?= *Answer:)', tossups, flags=regex.IGNORECASE):
        data['tossups'].append({'question': i})
    print('Processed', len(data['tossups']), 'tossups')

    if has_category_tags:
        for i, j in enumerate(regex.findall(r'(?<=Answer: +).+?(?= *<.*>)', tossups, flags=regex.IGNORECASE)):
            data['tossups'][i]['answer'] = j
    else:
        for i, j in enumerate(regex.findall(r'(?<=Answer: +).+?(?= *\d{1,2}\.| *TB\.| *Tiebreaker\.)', tossups, flags=regex.IGNORECASE)):
            data['tossups'][i]['answer'] = j

    for i, j in enumerate(regex.findall(r'<.*?>', tossups, flags=regex.IGNORECASE)):
        cat = get_subcategory(j)
        if len(cat) == 0:
            print(i+1, "tossup error finding the subcategory", j)
        else:
            data['tossups'][i]['subcategory'] = cat
            data['tossups'][i]['category'] = subcat[cat]


    if has_category_tags:
        for i in regex.findall(r'(?<=> *\d{1,2}\. *|TB\. *|Tiebreaker\. *|Extra\. *).+?(?= *\[[10hme]+\])', bonuses, flags=regex.IGNORECASE):
            data['bonuses'].append({'leadin': i})
    else:
        for i in regex.findall(r'(?<= +\d{1,2}\. +|TB\. +|Tiebreaker\. +|Extra\. +).+?(?= *\[[10hme]+\])', bonuses, flags=regex.IGNORECASE):
            data['bonuses'].append({'leadin': i})
    print('Processed', len(data['bonuses']), 'bonuses')

    if has_category_tags:
        for i, j in enumerate(regex.findall(r'(?<=Answer: *).+?(?= *\[[10hmeHME]+\]|<.*>)', bonuses, flags=regex.IGNORECASE)):
            if i % 3 == 0:
                data['bonuses'][i//3]['answers'] = [j]
            else:
                data['bonuses'][i//3]['answers'].append(j)
    else:
        for i, j in enumerate(regex.findall(r'(?<=Answer: +).+?(?= *\[[10hmeHME]+\]| *\d{1,2}\.)', bonuses, flags=regex.IGNORECASE)):
            if i % 3 == 0:
                data['bonuses'][i//3]['answers'] = [j]
            else:
                data['bonuses'][i//3]['answers'].append(j)

    for i, j in enumerate(regex.findall(r'(?<=\[[10hme]+\] +).+?(?= *Answer:)', bonuses, flags=regex.IGNORECASE)):
        if i % 3 == 0:
            data['bonuses'][i//3]['parts'] = [j]
        else:
            data['bonuses'][i//3]['parts'].append(j)

    for i, j in enumerate(regex.findall(r'<.*?>', bonuses, flags=regex.IGNORECASE)):
        cat = get_subcategory(j)
        if len(cat) == 0:
            print(i+1, "bonus error finding the subcategory", j)
        else:
            data['bonuses'][i]['subcategory'] = cat
            data['bonuses'][i]['category'] = subcat[cat]

    time_now = time.perf_counter()

    if not has_category_tags:
        for bonus in data['bonuses']:
            category, subcategory, question = classify_question(bonus['leadin'] + bonus['parts'][0] + bonus['parts'][1] + bonus['parts'][2], is_tossup=False)
            bonus['category'] = category
            bonus['subcategory'] = subcategory

            print(category, subcategory)

        for tossup in data['tossups']:
            category, subcategory, question = classify_question(tossup['question'], is_tossup=True)
            tossup['category'] = category
            tossup['subcategory'] = subcategory

            print(category, subcategory)

    print(f'it took {time.perf_counter() - time_now} seconds to classify')
    json.dump(data, g)