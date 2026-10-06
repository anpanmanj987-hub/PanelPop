"""Japanese and English text for every message a person can see."""

LANGUAGES = ('ja', 'en')

MESSAGES = {
    # Safety state
    'expired': ('表示期限が切れました。表示の更新を待ってください。', 'This view has expired. Wait for it to refresh.'),
    'target_hidden': ('対象は非表示・最小化、または無効です。PCで確認してください。', 'The target window is hidden, minimized or invalid. Check it on the PC.'),
    'target_too_large': ('対象が大きすぎます（最大1600万画素）。', 'The target window is too large (16 megapixels at most).'),
    'region_count': ('領域は1〜4個必要です。', 'Select one to four regions.'),
    'region_format': ('領域は整数の x, y, 幅, 高さで指定してください。', 'Give each region as whole-number x, y, width and height.'),
    'region_outside': ('領域がウィンドウの外にあります。', 'A region lies outside the window.'),
    'resume_on_pc': ('PCで再開してください。', 'Resume on the PC.'),
    'not_configured': ('PCで対象ウィンドウと領域を設定してください。', 'Choose a window and regions on the PC.'),
    'target_changed': ('対象の位置・サイズ・状態が変わりました。PCで再開してください。', 'The target window moved, resized or changed state. Resume on the PC.'),
    'target_covered': ('対象が他のウィンドウに遮られています。PCで確認して再開してください。', 'Another window covers the target. Check the PC and resume.'),
    'inspection_failed': ('対象の検査に失敗しました', 'Could not inspect the target'),
    'invalid_window': ('対象ウィンドウが無効です。', 'The selected window is not valid.'),
    'covered_bring_front': ('対象が遮られています。前面に表示してください。', 'The target is covered. Bring it to the front.'),
    'capture_size_changed': ('撮影サイズが変わりました。', 'The captured size changed.'),
    'capture_failed': ('撮影に失敗しました', 'Capture failed'),
    'invalid_frame': ('この表示は無効になりました。表示の更新を待ってください。', 'This view is no longer valid. Wait for it to refresh.'),
    'invalid_panel': ('領域番号が無効です。', 'Unknown panel.'),
    'view_only': ('閲覧専用です。操作の許可はPC側で設定します。', 'View only. Control can be allowed on the PC.'),
    'invalid_tap': ('タップが領域外、または無効です。', 'The tap was outside the panel or invalid.'),
    'config_changed': ('設定が変わりました。表示の更新を待ってください。', 'The settings changed. Wait for the view to refresh.'),
    'input_failed': ('入力に失敗しました', 'Input failed'),
    'control_bool': ('操作許可は true か false で指定してください。', 'Control must be true or false.'),
    'stopped': ('PCで停止しました。再開もPCで行います。', 'Stopped on the PC. Resume on the PC as well.'),
    'configure_first': ('先に対象を設定してください。', 'Choose a target first.'),
    'process_changed': ('対象のプロセスが変わりました。選び直してください。', 'The target process changed. Choose the window again.'),
    'covered': ('対象が遮られています。', 'The target is covered.'),
    'changed_during_capture': ('撮影中に対象が変わりました。', 'The target changed during capture.'),
    'demo_target': ('デモの対象は1つだけです。', 'The demo has a single target window.'),
    # Windows backend
    'windows_required': ('Windows 10/11が必要です。他のOSでは --demo を指定してください。', 'Windows 10 or 11 is required. On other systems, use --demo.'),
    'dpi_failed': ('モニターごとのDPI対応を有効にできませんでした。', 'Could not enable per-monitor DPI awareness.'),
    'window_gone': ('対象ウィンドウがありません。', 'The target window no longer exists.'),
    'process_unknown': ('対象のプロセスを取得できません。', 'Could not identify the target process.'),
    'client_rect_failed': ('ウィンドウの位置を取得できません。', 'Could not read the window position.'),
    'changed_before_input': ('クリックの直前に対象が変わりました。', 'The target changed just before the click.'),
    'cursor_move_failed': ('カーソルを移動できませんでした。', 'Could not move the cursor.'),
    'changed_after_move': ('カーソルの移動後に対象が変わりました。', 'The target changed after the cursor moved.'),
    'cursor_mismatch': ('カーソルの実際の位置を確認できない、または指定位置と一致しません。', 'The cursor is not where it should be, or its position could not be read.'),
    'sendinput_failed': ('SendInputが完了しませんでした（管理者権限のアプリによる制限を含む）。', 'SendInput did not complete (an elevated app may block it).'),
    # HTTP
    'url_too_long': ('URLが長すぎます。', 'The URL is too long.'),
    'host_refused': ('このHostまたは接続元は許可されていません。', 'This host or origin is not allowed.'),
    'origin_mismatch': ('Originが一致しません。', 'The Origin does not match.'),
    'absolute_url': ('絶対URLは使用できません。', 'Absolute URLs are not accepted.'),
    'bad_query': ('クエリが無効です。', 'The query is invalid.'),
    'admin_loopback': ('PC設定はこのPCからしか開けません。', 'PC settings are only available on this PC.'),
    'bad_token': ('接続トークンが無効です。PCに表示されたURLかQRコードから開いてください。', 'Invalid token. Open the URL or QR code shown on the PC.'),
    'json_required': ('application/json で送信してください。', 'Send application/json.'),
    'bad_length': ('Content-Lengthが無効です。', 'Invalid Content-Length.'),
    'too_large': ('送信データが大きすぎます。', 'The request is too large.'),
    'bad_json': ('JSONが無効です。', 'Invalid JSON.'),
    'bad_input': ('入力の形式が無効です。', 'The input is not in the expected format.'),
    'server_error': ('処理に失敗しました。PCの対象と設定を確認してください。', 'Something went wrong. Check the target and settings on the PC.'),
    'no_cors': ('CORSは許可していません。', 'CORS is not allowed.'),
    'not_found': ('ページがありません。', 'Not found.'),
    'no_action': ('その操作はありません。', 'Unknown action.'),
}


def language(header):
    """Pick ja or en from an Accept-Language header; anything else is English."""
    for part in (header or '').split(','):
        tag = part.split(';')[0].strip().lower()
        if tag.startswith('ja'):
            return 'ja'
        if tag.startswith('en'):
            return 'en'
    return 'en'


def text(key, lang='en', detail=''):
    message = MESSAGES[key][LANGUAGES.index(lang) if lang in LANGUAGES else 1]
    if not detail:
        return message
    return f'{message}: {detail}' if lang != 'ja' else f'{message}：{detail}'
