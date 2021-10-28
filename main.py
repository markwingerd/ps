import re
import sys
import unicodedata

from bs4 import BeautifulSoup
import requests

from item import ItemFactory

MARKET_SELL_URL = 'http://boards.nexustk.com/MarketS/'


def parse_text(text):
    """ Makes sure the text is as clean as can be """
    text = unicodedata.normalize('NFKD', text) # Removes \xa0
    text = text.replace('<b>', '')
    text = text.encode('utf-8').strip()
    text = re.sub(r'[^\x00-\x7f]', r'', text)
    # remove commas which wreck csv
    text = re.sub(r',', '.', text)
    return text


def get_last_id():
    """ Gets the last scraped post number """
    with open('.lastidscraped.txt', 'r') as f:
        last_id = f.read()
    try:
        return int(last_id)
    except:
        return 0


def set_last_id(id_):
    """ Saves the last scraped post number """
    # pass
    with open('.lastidscraped.txt', 'w') as f:
        f.write(str(id_))


def get_sell_posts(soup):
    """ Gets all posts on the first page
    Returns a list of [post_number, author, title, url]
    """
    output = []
    last_id = get_last_id()
    ids = []
    for row in soup.find_all('tr'):
        tds = row.find_all('td')
        if len(tds) != 4:
            continue
        post_number = parse_text(tds[0].a.text)
        author = parse_text(tds[2].a.text)
        title = parse_text(tds[3].a.text)
        url = tds[0].a['href']
        if int(post_number) > last_id:
            output.append([post_number, author, title, url])
        ids.append(int(post_number))
    set_last_id(ids[0])
    return output


if __name__ == '__main__':
    resp = requests.get(MARKET_SELL_URL)
    if resp.status_code != 200:
        print 'Error retrieving sell board'
        sys.exit()

    soup = BeautifulSoup(resp.text, 'html.parser')
    sell_posts = get_sell_posts(soup)

    #### Get each post, scan each line of body, see if an item is there
    items = []
    for post in sell_posts[:]:
        resp = requests.get(MARKET_SELL_URL + post[3])
        soup = BeautifulSoup(resp.text, 'html.parser')
        sell_post = soup.find_all('tr')[4].text
        # print sell_post
        for line in sell_post.split('\n'):
            line = parse_text(line)
            item = ItemFactory.get(post, line)
            if item:
                items.append(item)

    # Sort by filename
    items_by_filename = {}
    for item in items:
        filename = item.get_filename()
        try:
            items_by_filename[filename].append(item)
        except KeyError:
            items_by_filename[filename] = [item]

    # Print
    for filename, items in items_by_filename.iteritems():
        print filename
        # items = sorted(items, key=lambda item: item.mark)
        # for item in items:
        #     print '{}:{}\t {}'.format(item.post_id, item.post_author, item)

    for filename, items in items_by_filename.iteritems():
        items = sorted(items, key=lambda item: item.mark)
        with open('logs/{}.csv'.format(filename), 'a+') as f:
            for item in items:
                f.write('{},{},{}\n'.format(
                    item.text,
                    item.post_author,
                    item.post_id
                ))
