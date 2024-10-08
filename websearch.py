from bs4 import BeautifulSoup as bs
from googlesearch import search
from rank_bm25 import BM25Okapi
import string
from sklearn.feature_extraction import _stop_words
from tqdm.autonotebook import tqdm
import numpy as np
import concurrent.futures
import time
import requests
import os

os.environ["OPENAI_API_KEY"] = ""
from openai import OpenAI
client = OpenAI()

def bm25_tokenizer(text):
    tokenized_doc = []
    for token in text.lower().split():
        token = token.strip(string.punctuation)

        if len(token) > 0 and token not in _stop_words.ENGLISH_STOP_WORDS:
            tokenized_doc.append(token)
    return tokenized_doc

def BM25func(passages,query):
  tokenized_corpus = []
  for passage in tqdm(passages):
      tokenized_corpus.append(bm25_tokenizer(passage))
  bm25 = BM25Okapi(tokenized_corpus)
  bm25_scores = bm25.get_scores(bm25_tokenizer(query))
  print("BM25 SCORES:",len(bm25_scores))
  try:
      top_n = np.argpartition(bm25_scores, -10)[-10:]
  except:
      try:
          top_n = np.argpartition(bm25_scores, -4)[-4:]
      except:
          top_n = np.argpartition(bm25_scores, -2)[-2:]
      
  bm25_hits = [{'corpus_id': idx, 'score': bm25_scores[idx]} for idx in top_n]
  bm25_hits = sorted(bm25_hits, key=lambda x: x['score'], reverse=True)
  bm25_passages = []
  for hit in bm25_hits:
      bm25_passages.append(' '.join(passages[hit["corpus_id"]].split()[:100]))
  print(bm25_passages)
  return bm25_passages

def scraper(url,con,DataWrtUrls,passages):
  # try:   
      print("Scrapper running")
      session = requests.Session()
      session.headers['User-Agent']
      my_headers = {"User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14685.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.4992.0 Safari/537.36",
          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"}
      result = session.get(url, headers=my_headers, verify=False, timeout=3)
      doc = bs(result.content, "html.parser")
      contents = doc.find_all("p")       
      for content in contents:
          passages.append(content.text)
          con.append(content.text + "\n")
          
      DataWrtUrls[url] = str(con)
  # except:
  #     pass

def internet(customer_message):
          bi_encoder_searched_passages=""
          urls = []
          passages = []
          con = []
          start =  time.time()
          search_results = list(search(customer_message, tld="com", num=10, stop=10, pause=0.75))  #URL searching
          for j in search_results:
              urls.append(j)
          print("URLS=",urls)
          DataWrtUrls = {}
          passages=[]
          time_for_scraping = time.time()
          with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
              for url in urls:
                  executor.submit(scraper,url,con,DataWrtUrls,passages)
          print("Passages=",passages)
          print("time for scraping: ",time.time()-time_for_scraping)
          passages2 = []
          i = 0
          try:
              i=0
              for x in range(1,12):
                  i = i
                  Z = ""
                  P = ""
                  while len(Z) <=80:
                      P += (passages[i])
                      Z = P.split()
                      i+=1
                  passages2.append(P)
          except:
              try:
                  i=0
                  for x in range(1,8):
                      i = i
                      Z = ""
                      P = ""
                      while len(Z) <=80:
                          P += (passages[i])
                          Z = P.split()
                          i+=1
                      passages2.append(P)
              except:
                  i=0
                  for x in range(1,2):
                      i = i
                      Z = ""
                      P = ""
                      while len(Z) <=80:
                          P += (passages[i])
                          Z = P.split()
                          i+=1
                      passages2.append(P)
          end  = time.time() - start
          
          start = time.time()
          bi_encoder_searched_passages = BM25func(passages2,customer_message)
            # if not prod: print(bi_encoder_searched_passages)
          end = time.time()
          print(f"Runtime of the program is {end - start}")
          lfqa_time = time.time()
          question = customer_message
          print("Length of bi_encoder:", len(bi_encoder_searched_passages))
          if len(bi_encoder_searched_passages) >= 7:
                  supporting_texts = "Supporting Text 1: "+str(bi_encoder_searched_passages[0])+"\nSupporting Text 2: "+str(bi_encoder_searched_passages[1])+"\nSupporting Text 3: "+str(bi_encoder_searched_passages[2])+"\nSupporting Text 4: "+str(bi_encoder_searched_passages[3])+"\nSupporting Text 5: "+str(bi_encoder_searched_passages[4])+"\nSupporting Text 6: "+str(bi_encoder_searched_passages[5])+"\nSupporting Text 7: "+str(bi_encoder_searched_passages[6])
          else:
              supporting_texts = ""
              for i in range(len(bi_encoder_searched_passages)):
                  supporting_texts += "Supporting Text "+str(i+1)+": "+str(bi_encoder_searched_passages[i])+"\n"
          print(supporting_texts)
          UrlWrtRank = {}
          k = 0
          for i in range(len(bi_encoder_searched_passages)):
              for url, value in DataWrtUrls.items():
                  string = str(value)
                  if k == 7:
                      break
                  if string.find(str(bi_encoder_searched_passages[i]))!=-1:
                      UrlWrtRank[k]=url
                      k += 1
                  if string.find(str(bi_encoder_searched_passages[i]))==-1:
                      UrlWrtRank[k]=url
                      k += 1
          completion = client.chat.completions.create(
              model="gpt-4-1106-preview",
                messages=[{"role": "system", "content": "You are a helpful assistant that can Generate answer to a question from multiple supporting texts. Strictly use the content given in the supporting texts to generate the answer. Please do not include your opinion. You will also provided with the URL sources from where the news was retrieved which you need to return in the response.  For each paragraph, include a bracketed number, such as [1], [2], [3], to indicate the source of the information."},
          {"role": "user", "content": "Generate answer to the question: "+str(question)+"\n\nSupporting Texts\n"+str(supporting_texts)+"\n\nURL sources:"+str(UrlWrtRank)}])
          output=completion.choices[0].message.content
          print(output)
          return(output)
            
            
      