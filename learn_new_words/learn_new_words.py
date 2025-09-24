import random
import tkinter.filedialog

import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer 

from docx import Document
from googletrans import Translator
from pypdf import errors, PdfReader
from wordfreq import zipf_frequency

lemmatizer = WordNetLemmatizer()
translator = Translator()
src_lang = "en"
dest_lang = "ru"

# верхняя и нижняя границы частотности слов выбираются в зависимости от уровня студента,
# текущие значения подходят для студента уровня C1
frq_lower = 1.5
frq_upper = 2.7

answer_options = [
    "Good!\n",
    "Very good!\n",
    "Good! let's move on to the next one.\n",
    "Nice!",
    "Impressive!"
]

def get_text():
    """Извлечь текст из pdf файла.
    
    Пользователь выбирает файл и указывает, с каким диапазоном страниц работать. Текст извлекается из pdf и сохраняется
    в переменную text.
    """
    while True:
        try:
            address = tkinter.filedialog.askopenfilename(title='Please choose a pdf file.')
            pdfFileObj = open(address, 'rb') 
            pdfReader = PdfReader(pdfFileObj)   

            print(f'This file contains {len(pdfReader.pages)} pages.')
            num = input('How many would you like to process? Give me the start page and the end page like this: 1-40. ')
            hyphen = num.find('-')
            start = int(num[:hyphen])
            end = int(num[hyphen+1:])

            text = ''
            for i in range(start, end+1):
                text += pdfReader.pages[i-1].extract_text()

            text = text.replace('\n', '')
            pdfFileObj.close()
            
            return text

        except FileNotFoundError:
            print("It seems like this file doesn't exist.")
            break

        except errors.PdfReadError:
            print("It seems like this is not a pdf file. Please choose a pdf file.")
            
        except IndexError:
            print("The range seems wrong. Perhaps the file doesn't contain this number of pages. Please try again.")


def get_word_set(text):
    """Составить набор слов, которые пользователь скорее всего не знает.
    
    Текст токенизируется: строка text делится на слова с помощью nltk, 
    результат сохраняется в списке words. Затем составляется список pos, 
    в котором частеречные теги слов хранятся в том же порядке, что сами слова в списке words. 
    Затем из списка words удаляются числа и имена собственные (определяются по регистру),
    а также самые частотные (так как скорее всего известны пользователю) и наоборот самые редкие слова 
    (вероятно их изучение еще не релевантно для студента среднего уровня).
    """
    words = nltk.word_tokenize(text)
    pos = [nltk.pos_tag([word]) for word in words]
    word_set = set({})
    for word in words:
        if word.isalpha() and frq_lower < zipf_frequency(word, src_lang) <= frq_upper and word.islower():
            word_set.add(word)
    
    return word_set

def get_sentence_list(text):
    """Текст делится на предложения, результат сохраняется в списке строк sentence_list."""
    sentence_list = nltk.sent_tokenize(text)
    return sentence_list

def find_sent(word, sentence_list):
    """Найти предложение из текста, в котором используется слово word."""
    for sent in sentence_list:
        if word in nltk.word_tokenize(sent):
            return sent
        
def get_nltk_tag(word, tagged_sent):
    """Найти частеречный тег слова word в предложении с частеречной разметкой tagged_sent."""
    for item in tagged_sent:
        if word in item:
            return item[1]
        
def nltk_tag_to_wordnet_tag(nltk_tag):
    """Преобразовать частеречный тег nltk в частеречный тег WordNet."""
    if nltk_tag.startswith("J"):
        return wordnet.ADJ
    elif nltk_tag.startswith("V"):
        return wordnet.VERB
    elif nltk_tag.startswith("N"):
        return wordnet.NOUN
    elif nltk_tag.startswith("R"):
        return wordnet.ADV
    else:
        return None
    
def get_lemma(word, sentence_list):
    """Лемматизировать слово (привести к начальной форме).
    
    Программа находит предложение, в котором используется слово word.
    Предложение токенизируется, каждому токену назначается частеречный тег.
    Затем частеречные теги nltk преобразуются в теги WordNet.
    Слово лемматизируется с помощью лемматизатора WordNet.
    В случае, если это глагол, добавляется инфинитивная частица to.
    """
    try:
        sent = find_sent(word, sentence_list)
        sent_tokens = nltk.word_tokenize(sent)
        tagged_sent = nltk.pos_tag(sent_tokens)
        nltk_tag = get_nltk_tag(word, tagged_sent)
        wordnet_tag = nltk_tag_to_wordnet_tag(nltk_tag)
        if wordnet_tag == wordnet.VERB:
            result = f"to {lemmatizer.lemmatize(word, wordnet_tag)}"
        else:
            result = f"{lemmatizer.lemmatize(word, wordnet_tag)}"
        return result 
    
    except:
        return "Not found"
    
def translate_options(word):
    """Перевести слово word с английского на русский с помощью Google translate.
    
    Если переводчик предлагает несколько вариантов перевода слова, 
    они сохраняются в список options с порядковым номером.
    Если вариант только один, то options - строка, содержащая этот вариант.
    """
    translation = translator.translate(word, src=src_lang, dest=dest_lang)
    
    if translation.extra_data["all-translations"]:
        options = translation.extra_data["all-translations"][0][1]
        if translation.text not in translation.extra_data["all-translations"][0][1]:
            options.insert(0, translation.text)
        for i in range(len(options)):
            options[i] = f"{i+1}. {options[i]}"
    else:
        options = translation.text
        
    return options

def correct_trans(options, list_of_num):
    """Выбрать все правильные варианты перевода слова.
    
    options - список возможных переводов, 
    list_of_num - список чисел, которые пользователь указал как номера верных вариантов перевода.
    
    Функция возвращает список corr_trans - список верных вариантов перевода без порядкового номера.
    """
    corr_trans = []
    for num in list_of_num:
        corr_trans.append(options[int(num) - 1][3:])
    return corr_trans

def analyze(word_set, sentence_list):
    """Выбрать новые для пользователя слова и верный перевод для них.
    
    word_set - множество потенциальных новых слов (set).
    sents - список предложений исходного текста.
    
    Студент указывает число новых слов, которые хочет записать - words_needed.
    Программа поочередно показывает студенту слова из набора word_set вместе с предложением, где они встретились.
    """
    new_words = {}
    
    print(f"I have found {len(word_set)} words you might not know.")
    words_needed = int(input("How many words do you need? Type a number. "))
    
    for word in word_set:
        while len(new_words) < words_needed:
            
            # слово лемматизируется, а если лемму не удалось получить либо эта лемма уже есть в new_words, 
            # это слово пропускается, и цикл начинается заново
            lemma = get_lemma(word, sentence_list)
            if lemma == "Not found" or lemma in new_words:
                break
                
            the_sent = find_sent(word, sentence_list).strip().replace('\n', ' ')
            print('\n', lemma, '\n', the_sent, '\n')
            answer = input("Do you know this word? Type yes or no. If the word form is incorrect, type 0.").lower().strip()
            

            # если пользователь знает слово, он получает ответ от программы, слово пропускается,
            # и цикл начинается заново
            if answer == "yes":
                print(random.choice(answer_options))
                break
                
            if answer == "0":
                lemma = input("Please, type in the correct form. ").lower().strip()
                
            # если пользователь не знает слово
            if answer == "no" or answer.strip() == "0":   
                if lemma.startswith('to '):
                    trans_opt = translate_options(lemma)
                else:
                    trans_opt = translate_options(word)
                
                # если есть несколько вариантов перевода, пользователь выбирает верные либо вводит свой вариант
                if type(trans_opt) == list:
                    print(f"Here are the translation options: {trans_opt}")
                    num_trans = input("""Which one do you find correct? Give me a number or a list of numbers separated by comma. Type 0 if none are correct. """).split(', ')
                    while True:
                        try:
                            if num_trans == ["0"]:
                                corr_trans = input("Type in your translation here. ").lower().strip()
                            else:
                                corr_trans = correct_trans(trans_opt, num_trans)
                                
                            print(f"Alright, so your preferred translation is {corr_trans}.")
                            new_words[lemma] = corr_trans, the_sent
                            print(f"Good, so now you have {len(new_words)} words out of {words_needed}!")
                            break

                        except:
                            print("That wasn't a viable answer option. Please try again.")
                    

                
                # если есть только один вариант перевода, пользователь указывает, верный он или нет,
                # если нет, то вводит свой вариант
                else:
                    print(f"The translation of this word is {trans_opt}")
                    feedback = input("Is it correct? Type yes or no. ").lower().strip()
                    if feedback == "yes":
                        new_words[lemma] = trans_opt, the_sent
                    elif feedback == "no":
                        corr_trans = input("Type in your translation here. ").lower().strip()
                        new_words[lemma] = corr_trans, the_sent

                    print(f"Good, so now you have {len(new_words)} words out of {words_needed}!") 

    print("Seems like you have all the words you need!")
        
    return new_words
            
def save_to_file(new_words):
    """Сохранить в файл docx таблицу с новыми словами, их переводом и примером предложения."""
    
    name = input("What should I call the document? ").strip()
    doc_name = name + '.docx'
    
    word_document = Document()
    
    table = word_document.add_table(len(new_words), 4)
    i = 0
    j = 1
    
    for item in new_words:
        row = table.rows[i]
        row.cells[0].text = f'{j}'
        row.cells[1].text = item
        
        if type(new_words[item][0]) == str:
            row.cells[2].text = new_words[item][0]
        else:
            row.cells[2].text = ", ".join(new_words[item][0])
        row.cells[3].text = new_words[item][1]
        i += 1
        j += 1
        
    word_document.save(doc_name)
    
    print(f"Your words, their translations and example sentences have been saved to {doc_name}. Make sure to check it out!")
    
def run():
    """Запустить программу."""
    
    text = get_text()
    if text:
        word_set = get_word_set(text)
        sentence_list = get_sentence_list(text)
        new_words = analyze(word_set, sentence_list)
        
        if new_words:
            save_to_file(new_words)

if __name__ == "__main__":
    run()
