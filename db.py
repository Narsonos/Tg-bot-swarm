import sqlite3
from dataclasses import dataclass




@dataclass
class AccessToken:
    token: str 
    valid: bool 

@dataclass
class Community:
    link: str

@dataclass
class Settings:
    id: int #pretty much a dummy value
    maxlikes: int 
    maxreposts: int 
    keywords: str

@dataclass
class KrutkaSettings:
    maxlikes: int 
    maxreposts: int 
    posts: list


class DatabaseWrapper():
    def __init__(self, config):
        self.conn = sqlite3.connect(config.dbfile)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS AccessTokens (
                token TEXT PRIMARY KEY,
                valid BOOL NOT NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Communities (
                link TEXT PRIMARY KEY
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Settings (
                id INTEGER PRIMARY KEY CHECK (id = 0),
                maxlikes INTEGER,
                maxreposts INTEGER,
                keywords TEXT
            )
        ''')

        self.cursor.execute('''
            INSERT INTO Settings (id,maxlikes,maxreposts,keywords)
            SELECT 0,0,0,'-'
            WHERE NOT EXISTS (SELECT 1 FROM Settings LIMIT 1);
        ''')
        self.conn.commit()


if __name__ == '__main__':
    re = '()'