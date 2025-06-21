import subprocess

def main():
    print("待機中...")
    try:
        while True:
            input("エンターキーでスタート")
            execute_local_script()
    except KeyboardInterrupt:
        print("exit")
def execute_local_script():
    """local.pyを実行"""
    try:
        result = subprocess.run(["python3", "local.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"local.pyに失敗: {e}")

if __name__ == "__main__":
    main()
    