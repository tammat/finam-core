from data.history_loader import HistoryLoader

if __name__ == "__main__":
    loader = HistoryLoader()
    loader.load("NGH6@RTSX", days=365*2, interval="M5")