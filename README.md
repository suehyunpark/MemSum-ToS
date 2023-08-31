# Extractive Summarization of Terms of Service

Term project for Fall 2022 Natural Language Processing (4190.678) course at Seoul National University

## Abstract
Terms of Service (ToS) are legal agreements between a service provider and a user. However, they are long and complex, often leading users to accept conditions they have not fully understood. This project aims to aid understanding the agreements while maintaining faithfulness to the legal context by developing an extractive summarization model tailored for ToS documents. Utilizing MemSum (Gu et al., 2022), a SOTA model for long document summarization on GovReport dataset, as a foundation, we introduce specialized improvements to better handle the legal jargon and complex sentence structures commonly found in ToS. Our model improves legal sentence encoding in two directions: 1) using legal word2vec embeddings (*MemSum-LegalEmb*) and 2) levaraging Transformer-based architecture via SBERT embeddings (*MemSum-SBERT*). For evaluation, we construct the ToS;DR dataset from a community-driven website in which contributors highlight salient points in various service terms. Experiments demonstrate that our enhanced model outperforms the baseline MemSum model, with ablation studies indicating further performance gain by expanding the reference summary set.


## Method
The base model is [MemSum](https://github.com/nianlonggu/MemSum) ([Gu et al., 2022](https://aclanthology.org/2022.acl-long.450/)).
Our approach is to improve the Local Sentence Encoder (LSE) module of MemSum by the following:
1. integrating legal domain word2vec embedding models from [SigmaLaw](https://osf.io/qvg8s/) ([Sugathadasa et al., 2017](https://www.researchgate.net/publication/317399369_Synergistic_Union_of_Word2Vec_and_Lexicon_for_Domain_Specific_Semantic_Similarity)), which we call *MemSum-LegalEmb*
2. integrating SBERT sentence embeddings provided by [sentence-transformers/all-mpnet-base-v2](https://huggingface.co/sentence-transformers/all-mpnet-base-v2), which we call *MemSum-SBERT*

## Dataset
For validation, we run experiments on [GovReport](https://gov-report-data.github.io/) ([Huang et al., 2021](https://aclanthology.org/2021.naacl-main.112)), the dataset which our baseline reports SOTA on and tests our model's performance on a domain with characteristics similar to ToS.  
For main evaluation, we build the ToS;DR dataset by scraping ToS documents and user highlighted text in the [tosdr.org](https://tosdr.org/).
In a single ToS document,
- Gold summary is composed of sentences highlighted by contributors in the ToS;DR community.
- Oracle summaries are candidate summaries built by sequentially selecting the optimal sentence that maximally improves the average ROUGE score once added to the current subset of selected sentences. ROUGE scores include ROUGE-1, 2, and L for measuring unigram, bigram, and longest common subsequence.

|Train | Valid | Test |
|---------------|--------------|---------------|
| 1,611 | 202  | 201  |

tosdr.org is licensed under the [GNU Affero General Public License v3.0]((https://github.com/tosdr/edit.tosdr.org/blob/master/LICENSE)) (AGPL-3.0), but currently we are not providing our ToS;DR dataset. To view the dataset format, you can head to our repo's [tosdr-dataset/sample_data](https://github.com/suehyunpark/MemSum-ToS/tree/main/tosdr-dataset/sample_data) directory.

### Hyperparameters
We train our model using the Adam optimizer with β1 = 0.9, β2 = 0.999, fixed learning rate 0.0001, weight decay 0.000001, and choose the best checkpoint based on validation performance. For dataset-specific hyperparameters, we select the values optimal after tuning in baseline experiments:
| Dataset                        | `max_sentence_num` | `max_sequence_len` | `p_stop_threshold`           | `max_extracted_sentences_per_document` |
| ----------------------------------- | ---------------- | ---------------- | -------------------------- | ------------------------------------ |
| GovReport                           | 500              | 100              | 0.6                        | 22                                   |
| TOS;DR                              | 300              | 50               | 0.6                        | 13                                   |


## Experiment results
On GovReport, *MemSum-LegalEmb* shows comparable performance. *MemSum-SBERT* approaches the baseline performance even after training for only 5 epochs.

| Model           | Best Epoch | ROUGE-1 | ROUGE-2 | ROUGE-L |
| --------------- | ---------- | ------- | ------- | ------- |
| MemSum          | 50         | **0.5945**  | **0.2851**  | **0.5668**  |
| MemSum-LegalEmb | 40         | 0.5935  | 0.2823  | 0.5658  |
| MemSum-SBERT    | 5          | 0.5827  | 0.2465  | 0.5507  |

On ToS;DR, both of our models outperform the baseline.  
| Model           | ROUGE-1 | ROUGE-2 | ROUGE-L |
|-----------------|---------|---------|---------|
| MemSum          | 0.4075  | 0.2598  | 0.3937  |
| MemSum-LegalEmb | 0.4141  | 0.2705  | 0.4001  |
| MemSum-SBERT    | **0.4244**  | **0.2732**  | **0.4111**  |

Using both gold and oracle summaries as reference summaries are
better than just using gold summaries.  
| Model        | Reference Summaries | ROUGE-1 | ROUGE-2 | ROUGE-L |
|--------------|---------------------|---------|---------|---------|
| MemSum-SBERT | Gold                | 0.4168  | 0.2597  | 0.4026  |
| MemSum-SBERT | Gold + Oracle       | **0.4244**  | **0.2732**  | **0.4111**  |

For more results, please refer to our [slides](https://github.com/suehyunpark/MemSum-ToS/blob/main/slides.pdf).

## Contribution
- [Sue Hyun Park](https://github.com/suehyunpark): crawling and curating ToS;DR dataset, baseline MemSum experiments, hyperparameter tuning
- [Seungmin Han](https://github.com/seungminahan): MemSum-LegalEmb implementation and experiments
- [Heekang Park](https://github.com/heekangpark): MemSum-SBERT implementation and experiments
