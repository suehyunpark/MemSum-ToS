import pickle
import os
import pandas as pd
from tqdm import tqdm
from string import punctuation
from sacremoses import MosesTokenizer
from collections import defaultdict

punctuation_to_remove = punctuation.replace("'", "").replace("-", "")
tokenizer = MosesTokenizer(lang='en')

def dump_pickle(file_path, object):
    with open(file_path, 'wb') as handle:
        pickle.dump(object, handle)

def load_pickle(file_path):
    with open(file_path, 'rb') as handle:
        object = pickle.load(handle)
    return object


def gather_stats():
    PICKLE_PATH = "./pickles"
    stats = []
    # df = pd.DataFrame(columns=["block_num", "idx_in_block", "text_length", "summary_length", "ratio"])
    text_words_dict = defaultdict(list)
    summary_words_dict = defaultdict(list)
    
    for _, _, files in os.walk(PICKLE_PATH):
        for file in sorted(files):
            if file.startswith("tosdr_block"):
                print("Processing", file)
                block_idx = file.split('.')[0].split('_')[2]
                block_dicts = load_pickle(PICKLE_PATH + '/' + file)
                for i, block_dict in enumerate(tqdm(block_dicts)):
                    text = block_dict["text"]
                    summary = block_dict["summary"]
                    len_text, len_summary = len(text), len(summary)
                    
                    words_text = []
                    for sent in text:
                        words_per_sent = tokenizer.tokenize(sent.translate(str.maketrans('', '', punctuation_to_remove)))
                        if len(words_per_sent) < 10:
                            text_words_dict[len(words_per_sent)].append(words_per_sent)
                        words_text.extend(words_per_sent)
                    
                    words_summary = []
                    for sent in summary:
                        words_per_sent = tokenizer.tokenize(sent.translate(str.maketrans('', '', punctuation_to_remove)))
                        if len(words_per_sent) < 10:
                            summary_words_dict[len(words_per_sent)].append(words_per_sent)
                        words_summary.extend(words_per_sent)
                    len_words_text, len_words_summary = len(words_text), len(words_summary)
                    
                    stats.append({"block_idx": block_idx, 
                                  "idx_in_block": i, 
                                  "num_sent_text": len_text, 
                                  "num_sent_summary": len_summary,
                                  "sent_ratio": len_summary / len_text,
                                  "num_words_text": len_words_text,
                                  "num_words_summary": len_words_summary,
                                  "words_ratio": len_words_summary / len_words_text})
                    
    main_df =pd.DataFrame.from_records(stats)
    dump_pickle(PICKLE_PATH + '/tosdr_stats_main_df.pickle', main_df)
    
    text_words_df = pd.DataFrame.from_dict(text_words_dict, orient='index')
    dump_pickle(PICKLE_PATH + '/tosdr_stats_text_words_df.pickle', text_words_df)
    
    summary_words_df = pd.DataFrame.from_dict(summary_words_dict, orient='index')
    dump_pickle(PICKLE_PATH + '/tosdr_stats_summary_words_df.pickle', summary_words_df)


if __name__ == "__main__":
    gather_stats()