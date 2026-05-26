from databases import Database
from config.config import Config

config = Config()
database = Database(config.DATABASE_URL)
