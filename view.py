import pygame
import os

def fullscreen_on_external_monitor(status,count):
    """
    外部モニターにフルスクリーンでPygameウィンドウを表示する関数
    """
    

    # 全モニターの解像度を取得
    display_sizes = pygame.display.get_desktop_sizes()
    
    # 主モニター以外の最初の外部モニターを選択
    if len(display_sizes) > 1:
        external_monitor = display_sizes[1]  # 1つ目の外部モニター (インデックス 1)
        screen_width, screen_height = external_monitor
        os.environ["SDL_VIDEO_WINDOW_POS"] = f"{display_sizes[0][0]},0"  # 主モニター幅に基づく
    else:
        # 外部モニターがない場合は主モニターを使用
        print("外部モニターが見つかりません。主モニターでフルスクリーンを実行します。")
        screen_width, screen_height = display_sizes[0]

    # フルスクリーンモードのウィンドウ作成
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
    pygame.display.set_caption("External Monitor Fullscreen")

    # 背景の色
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)

    # メインループ
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        # 背景の塗りつぶし
        screen.fill(BLACK)

        # テキストの表示
        font = pygame.font.Font(None, 74)
        text = font.render("External Monitor Fullscreen", True, WHITE)
        text_rect = text.get_rect(center=(screen_width // 2, screen_height // 2))
        screen.blit(text, text_rect)

        # 描画の更新
        pygame.display.flip()

    # pygame.quit()

# 関数の呼び出し
fullscreen_on_external_monitor()