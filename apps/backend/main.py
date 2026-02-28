import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class Config:
    database_url: str
    secret_key: str
    debug: bool


def import_config():
    load_dotenv()

    config_module = os.getenv("CONFIG_MODULE", "config")
    try:
        config = __import__(config_module)
        return config
    except ImportError as e:
        print(f"Error importing config module '{config_module}': {e}")
        raise


if __name__ == "__main__":
    os.getenv
