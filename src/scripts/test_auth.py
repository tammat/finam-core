from finam_core.auth.token_manager import FinamTokenManager

def main():
    tm = FinamTokenManager()
    jwt = tm.get_token()
    print("JWT length:", len(jwt))
    print(jwt[:80])

if __name__ == "__main__":
    main()
