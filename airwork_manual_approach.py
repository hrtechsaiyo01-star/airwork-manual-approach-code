#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
airwork_manual_approach.py
===========================================================================
「手動アプローチ」タブ用の自動化モジュール。

仕様（ユーザー提供の指示書より要約）
---------------------------------------------------------------------------
1. 「手動アプローチ」タブは他のタブと異なり、⚙️設定タブのスプレッドシート ID
   ではなく、このファイル内に固定された `MANUAL_APPROACH_SHEET_ID` を対象
   データとして使う（GUI 側にはこの ID から作ったリンクを表示するのみ）。
   （⚙️設定タブの AirID / パスワードも使わず、対象シートの D列 / E列を使用する）

2. 対象スプレッドシートの列構成:
     A: COL_STATUS        （対応必要 / 対応済み / 求人ID見つからない / 正社員以外 /
                             未掲載 / 確認必要 / 候補者を表示できません）
     B: COL_COMPANY       会社名
     D: AirID
     E: パスワード
     F: COL_JOB_ID         求人番号
     G: アプローチ上限数
     H〜Q: 検索条件（希望勤務地 / 最終学歴 / 年以降 / 年以前 / 年齢下限 /
                       年齢上限 / スキル / 経験 / 保有資格 / 英会話レベル）
     S: 最終ログイン日時（bot が書き込む）
     T: 実際に送信したアプローチ人数（bot が書き込む）

3. 処理フロー（対応必要の行のみ）:
     a. 同じ会社（AirID/パスワードが同じ）なら再ログインせずそのまま続行。
     b. https://ats.rct.airwork.net/candidates に遷移し、求人一覧からF列の
        求人番号を探す（見つからなければページ送りしながら探す）。
        見つからない場合 → ステータスを「求人ID見つからない」に更新。
     c. 「候補者を探す」リンクを押せる場合はそのまま候補者検索画面へ。
        押せない場合は雇用形態を確認し、
          - 正社員以外 → ステータス「正社員以外」
          - 正社員     → 求人一覧(job_offers)で掲載状況を確認し、
                          未掲載 → ステータス「未掲載」
                          掲載中 → ステータス「確認必要」
     d. H〜Q列に検索条件が入っていれば「条件で候補者を探す」を開いて
        シートの値を入力し検索する。
     d'. H〜Q列に検索条件が一切入っていない場合、デフォルトの候補者一覧
        （「候補者を探す」クリック直後の画面）がそのまま表示されていれば
        それを使う。表示されていない場合（候補者のチェックボックスが
        1件も無い）は、「条件で候補者を探す」モーダルを開き、何も入力
        せずに「検索する」ボタンだけを押して候補者一覧を表示させる
        （UI上、モーダル経由での検索実行を挟まないと一覧が表示されない
        ケースがあるため）。
     d''. 上記のいずれの方法でも候補者一覧に「候補者を表示できません
        でした」という空表示メッセージが出ている、またはチェックボックス
        が1件も表示されない場合 → ステータスを「候補者を表示できません」
        に更新し、以降の処理を中断する。
     e. G列のアプローチ上限数に応じてチェックボックスを選択し
        「N人にまとめてアプローチ」ボタンを押す（50人単位でページ送り）。
     f. 送信件数を T列、処理日時を S列に記録し、ステータスを「対応済み」に更新。

---------------------------------------------------------------------------
⚠️ v2 変更点（ログイン処理の共通化）
---------------------------------------------------------------------------
以前のバージョンはこのファイル独自の `_login()` / `_ensure_driver()` を
実装しており、bot_core.py の実際のログインフォーム（OAuth ログイン画面、
`#account` / `#password` セレクタ）と一致しない汎用セレクタを使っていた
ため、ログインに失敗していた。

v2 では、ブラウザ起動・ログイン処理を独自実装するのをやめ、
`bot_core.AirWorkBotBase` のインスタンスに委譲する。これにより:
  * ログインフォームのセレクタ／URL の実装は bot_core.py の一箇所だけで
    保守すればよくなる（このファイルを直す必要がなくなる）。
  * bot_core.py 側でログイン方法が変わった場合も自動的に追従する。

このモジュール固有の処理（固定スプレッドシートの読み書き、候補者検索、
検索条件入力、一括アプローチ送信など）は従来どおりこのファイル内に残す。

---------------------------------------------------------------------------
⚠️ v3 変更点（「条件で候補者を探す」モーダルのセレクタを実HTMLに合わせて修正）
---------------------------------------------------------------------------
実際にモーダル（role="dialog", title="条件の設定"）を開いた状態のHTMLを
確認したところ、以下の点が判明したため修正した。

  * 最終学歴のチェックボックスは <input type="checkbox" name="1">〜
    <input type="checkbox" name="14"> のように "name=学歴コード" のみで
    構成されており、表示テキスト（"4年制大学" 等）は隣接する別の <span>
    に入っているだけで input 自体には紐付いていない。
    → 表示テキストで label を検索する方式は誤爆・取りこぼしの可能性が
      あるため、"学歴テキスト → コード番号" の対応表を持ち、
      name=コード番号 で直接チェックボックスを特定するように変更。

  * 英会話レベルの <select name="candidateFilter.englishLevelId"> は
    option の value が 1〜5 の数値で、表示テキストとは対応が非直感的
    （5=簡単な会話, 4=日常会話, 3=ビジネス会話, 2=ネイティブレベル,
      1=指定なし）。
    → 表示テキストではなく value で select_by_value するように変更。

  * モーダルが実際に開くまで明示的に待つようにし（開く前に要素を
    操作しようとして NoSuchElementException になるケースを防止）、
    各フィールドで要素が見つからなかった場合はこれまで以上に詳しく
    ログを出すようにした。

  * チェックボックスのクリックは通常の .click() だと他要素に隠れて
    ElementClickInterceptedException になることがあるため、
    JavaScript 経由のクリックに統一した。

  ⚠️ 希望勤務地（H列）については、v4 で2段階モーダル構造に対応済み
     （下記 v4 変更点を参照）。

---------------------------------------------------------------------------
⚠️ v4 変更点（希望勤務地：2段階モーダル構造への対応）
---------------------------------------------------------------------------
実際のUIを確認したところ、希望勤務地の設定は以下の2段階モーダル構造に
なっていることが判明したため、それに合わせて実装した。
  1) ラジオ hasUsingDesiredLocation=true（"設定する"）をクリックすると、
     #DesiredLocation 内に「設定する」という別ボタンが表示される。
  2) そのボタンをクリックすると、新しいモーダル
     role="dialog" aria-label="希望勤務地の設定" が開く。
  3) そのモーダルの中で、都道府県ごとに
     <input type="checkbox" name="青森県" value="02"> のように
     name 属性が都道府県名そのものになっているので、name で直接
     特定してチェックする（最大10個まで）。
  4) モーダル右下の「保存する」(type="submit") ボタンを押して確定する。

---------------------------------------------------------------------------
⚠️ v5 変更点（年齢下限／年齢上限のセレクタを value ベースに変更）
---------------------------------------------------------------------------
<option value="20">20歳</option> のように value 属性が年齢の数値その
ものであるため、表示テキストではなく value で直接指定する
（select_by_value）方が確実。シート側の値は半角数字を想定。

---------------------------------------------------------------------------
⚠️ v6 変更点（検索するボタンのセレクタ修正 ＋ 検索結果の条件反映チェック追加）
---------------------------------------------------------------------------
実際のUIを確認したところ、以下2点の不具合が判明したため修正した。

  * 「検索する」ボタンは <button data-theme="primary">検索する</button>
    のように実装されており、必ずしも <footer> 配下にあるとは限らなかった。
    そのため従来の `//footer//button[contains(., '検索する')]` という
    XPath ではボタンを見つけられず（NoSuchElementException が握り
    つぶされ）、実際には検索が実行されないままチェックボックスの選択・
    一括アプローチ送信に進んでしまうケースがあった。
    → `data-theme='primary'` を優先しつつ、旧セレクタもフォールバックと
      して残す XPath に変更し、`element_to_be_clickable` で明示的に待つ
      ようにした。

  * 検索実行後、画面上部に表示されるフィルターバー
    （`styles_filterBar__...` 配下の `styles_conditionText__...` /
    `styles_filterLabel__...`）に、実際に適用されている検索条件と
    検索結果件数が表示される。
    → 検索ボタンを押した後にこのフィルターバーを読み取り、シートに
      入力した条件（希望勤務地・最終学歴・卒業年・年齢・スキル・経験・
      保有資格・英会話レベル）が実際に画面へ反映されているかを
      ベストエフォートで照合するようにした（`_verify_applied_conditions`）。
      表示フォーマットはUI依存のため厳密な完全一致ではなく「入力値の
      文字列が含まれているか」で判定する簡易チェックとなる。
    → 照合の結果、反映されていない条件がある場合は、誤った対象へ
      アプローチを送信してしまうことを避けるため、チェックボックスの
      選択・一括アプローチ送信には進まず、ステータスを「確認必要」に
      更新して処理を中断するようにした。

---------------------------------------------------------------------------
⚠️ v7 変更点（「候補者を表示できませんでした」空表示メッセージの検知を追加）
---------------------------------------------------------------------------
実際のUIを確認したところ、検索条件に合致する候補者がいない場合や、
既に手動アプローチの送信上限に達している場合には、候補者一覧の代わりに

  <p class="styles_noSearchText__y7Hox">
    条件に合致する候補者がいないか、手動アプローチの上限に達したため、
    候補者を表示できませんでした。
  </p>

という空表示メッセージが表示されることが判明した。この状態のまま
チェックボックス選択・一括アプローチ送信の処理に進むと、対象0件のまま
無意味な処理を続けてしまう（または想定外のエラーになる）ため、
検索条件の有無に関わらず（＝条件検索した場合・条件なしでそのまま
候補者一覧に来た場合の両方で）、一括アプローチ送信の直前にこの
メッセージの有無を確認するようにした。

  * class名（styles_noSearchText__...）はビルドごとにハッシュ値が
    変わる可能性があるため、`class*=` の部分一致セレクタを優先しつつ、
    見つからない場合はメッセージ本文のテキスト内容でのフォールバック
    判定も行う（`_check_no_candidates_message`）。
  * 該当メッセージが見つかった場合は、ステータスを新設の
    「候補者を表示できません」（STATUS_NO_CANDIDATES）に更新し、
    一括アプローチ送信を行わずにその行の処理を終了する。

---------------------------------------------------------------------------
⚠️ v8 変更点（検索条件が未入力の場合の、候補者一覧が表示されない
             ケースへのフォールバックを追加）
---------------------------------------------------------------------------
H〜Q列に検索条件が一切入力されていない行では、従来「候補者を探す」を
クリックした直後のデフォルト画面をそのまま候補者一覧として扱っていた。
しかし実際の運用で、このデフォルト画面には候補者が1件も表示されない
（＝チェックボックスが存在しない）にもかかわらず、v7 で検知対象とした
「候補者を表示できませんでした」という空表示メッセージも出ていない、
という中間状態が確認された。

この状態は、UI側が「一度検索を実行する」という操作を経ないと候補者
一覧を描画しない仕様になっているためと考えられる。そのため v8 では、
検索条件が未入力の場合の処理を以下のように変更した。

  1. 「候補者を探す」クリック直後の画面で、候補者のチェックボックスが
     1件でも表示されていれば、従来どおりそのままそれを対象とする。
  2. 1件も表示されておらず、かつ「候補者を表示できませんでした」の
     メッセージも出ていない場合は、「条件で候補者を探す」モーダルを
     開き、H〜Q列の値は何も入力せずに（＝無条件のまま）「検索する」
     ボタンだけをクリックして、候補者一覧を強制的に表示させる
     （`_search_with_no_conditions`）。
  3. それでも候補者のチェックボックスが1件も表示されない場合
     （＝空表示メッセージが出た場合も、単に0件だった場合も含む）は、
     誤ってゼロ件のまま一括アプローチ処理へ進まないよう、ステータスを
     「候補者を表示できません」（STATUS_NO_CANDIDATES）に更新して
     その行の処理を終了する。

  なお、「検索する」ボタンのクリック処理自体は v6 で実装済みのロジック
  （data-theme='primary' セレクタ優先＋2回リトライ）を再利用するため、
  `_apply_conditions` 内にあった検索ボタンクリック処理を
  `_click_search_button_in_modal()` として切り出し、無条件検索の
  フォールバック（`_search_with_no_conditions`）と共通化した。

---------------------------------------------------------------------------
⚠️ v9 変更点（候補者チェックボックスの一括選択を高速化）
---------------------------------------------------------------------------
`_select_individual_checkboxes()` が候補者数（最大50件/ページ）分だけ
`execute_script()` をループで個別に呼んでいたため、1件ごとに
Selenium ⇔ ブラウザ間のIPCラウンドトリップが発生し、50件選択するのに
数秒かかることがあった。

v9 では、対象チェックボックス要素の配列をまとめて1回の
`execute_script()` に渡し、ブラウザ側のJavaScriptループで一括クリック
するように変更した（IPC往復を「N回」から「1回」に削減）。
  * Selenium は Python の list に入った複数の WebElement をそのまま
    `execute_script` の引数として渡すと、JS側では要素の配列として
    受け取れる仕様を利用している。
  * 個々の要素が stale だった場合でも他の要素の選択を止めないよう、
    JS側の forEach 内で try/catch している（従来の
    StaleElementReferenceException 握りつぶしと同等の挙動）。
  * `_select_all_checkbox()`（全選択チェックボックス1個をクリックする
    だけの処理）はもともと1回のクリックのみなので変更なし。

---------------------------------------------------------------------------
⚠️ v15/v16 変更点（一括アプローチ送信後、AirWork側の本物の成功通知を確認）
---------------------------------------------------------------------------
従来、「N人にまとめてアプローチ」の送信件数（total_sent）は、bot が
「まとめてアプローチ」ボタンをクリックできた（＝例外が出なかった）
かどうかだけをもとに、選択したチェックボックス数（take）を自己申告的に
積算していたに過ぎなかった。これはボタンのクリックに成功したことしか
保証しておらず、AirWork 側が実際に送信処理を受け付けたかどうかの
確認にはなっていなかった。

実際のHTMLを確認したところ、「まとめてアプローチ」ボタンを押すと、
画面上に以下のような本物の成功通知（トースト）が表示されることが
判明した。

  <div class="styles_success__iNsRZ styles_message__iyXyu" data-type="success">
    <div class="styles_messageItem__rI7WY">
      ...
      <span class="styles_messageSuccessTitle__c_ruF">送信完了</span>
      <span class="styles_messageDate__fd9wX">2026/7/14 11:15 送信</span>
    </div>
  </div>

v15 では、`_click_bulk_approach_button()` がボタンをクリックした後、
新設の `_read_success_message()` でこの成功通知の有無とテキスト内容
（タイトル・送信日時）を読み取り、ログに残すようにした。

v16 では、実際の運用でさらに次の点が判明したため、v15のロジックを
改良した。

  * 「まとめてアプローチ」の送信はAirWork側で非同期に処理される。
    ボタンを押した直後は本物の成功通知（送信完了）がすぐには出ず、
    代わりに以下のような「処理中」表示になる。

      <div class="styles_processingContainer__Zj2zt">
        <div class="styles_loader__NHNIO">...</div>
        <span class="styles_statusText__AF7cx">
          まとめてアプローチを送信中...
        </span>
        <button type="button" class="styles_refreshLink__TONqo ..."
                data-theme="text_primary">
          更新して状況を確認する
        </button>
      </div>

    この状態で、画面内の「更新して状況を確認する」ボタンを繰り返し
    クリックして状況を再取得し、本物の成功通知（送信完了）が表示
    されるまで待つ必要がある。実際に送信が完了しているかどうかは、
    この成功通知が出て初めて確定する。

  * v15では1回だけDOMを確認して通知の有無を判定していたため、処理中の
    タイミングでは誤って「通知が確認できませんでした」という警告を
    出してしまっていた。

  * v16では `_read_success_message()` 内でポーリングループを行うように
    変更した（最大60秒、2秒間隔）。
      1. 既に本物の成功通知（`_peek_success_message()`）が出ていれば、
         それを返して終了する。
      2. 処理中表示（`_is_processing()`）が出ていれば、
         「更新して状況を確認する」ボタン
         （`_click_refresh_status_button()`）をクリックして少し待ち、
         1に戻る。
      3. どちらの表示も無い場合は、表示切り替え中の過渡的なタイミング
         の可能性があるため、少し待って再確認する。
      4. 60秒経過しても成功通知が確認できなければ、WARN ログを出して
         処理を続行する（一括送信フロー自体は止めない）。

  * 通知が確認できた場合は、その内容（「送信完了」+ 日時）を
    OK レベルでログ出力する。これは bot の自己申告ではなく、
    AirWork 側が実際に処理を受け付けたことを示す確認材料となる。
  * class名（styles_success__..., styles_messageSuccessTitle__...,
    styles_messageDate__..., styles_processingContainer__...,
    styles_refreshLink__...）はビルドごとにハッシュ値が変わる可能性が
    あるため、他の箇所と同様に `class*=` の部分一致セレクタを使用する。

---------------------------------------------------------------------------
⚠️ v21 変更点（「まとめてアプローチ」ボタンクリック時の
             StaleElementReferenceException 対策）
---------------------------------------------------------------------------
実運用ログで、`_click_bulk_approach_button()` の冒頭、

    btn = self._wait(10).until(EC.element_to_be_clickable((...)))
    btn.click()

の `btn.click()` にて `selenium.common.exceptions.StaleElementReference
Exception` が発生し、その行の処理全体が失敗するケースが確認された。

原因は、v20 で追加した「送信完了後、ヘッダーの『まとめてアプローチ』
ボタンが再表示されるまで、処理中表示があれば都度『更新して状況を
確認する』を能動的にクリックし続けるループ」の直後などに、次バッチの
`_click_bulk_approach_button()` が呼ばれた際、`element_to_be_clickable`
の条件が一瞬 true になった直後に Reactが再描画して要素を差し替えて
しまい、取得済みの `WebElement` 参照が古くなる（stale になる）ことで
ある。従来は `TimeoutException` しか捕捉していなかったため、
`StaleElementReferenceException` はそのまま外側（`_process_row` の
`except Exception`）まで伝播し、その行の処理が丸ごと失敗していた。

v21 では、ボタンの取得とクリックをまとめて
`_locate_and_click_bulk_button()` に切り出し、
`StaleElementReferenceException` を捕捉した場合は要素を取得し直して
最大数回リトライするようにした（`ElementClickInterceptedException` の
場合の JS クリックへのフォールバックも維持）。

---------------------------------------------------------------------------
⚠️ v22 変更点（連続バッチ送信時、「まとめてアプローチ」ボタンの
             再表示待ちが短すぎて早期に諦めてしまう不具合の修正）
---------------------------------------------------------------------------
実運用ログで、1バッチ目（50人）の送信完了通知まで確認できたにも
かかわらず、続く2バッチ目で `_locate_and_click_bulk_button()` が
「まとめてアプローチ」ボタンを見つけられず、そのバッチをスキップして
しまうケースが確認された（結果として G列の目標人数に届かず
「確認必要」になっていた）。

原因は、1バッチ目送信後もヘッダー部分が「まとめてアプローチを
送信中...」という処理中表示のまま残り続けることがあり、
`_click_bulk_approach_button()` 末尾の再出現待ちループ（最大15秒）
だけでは解消しきらないタイミングがあった一方、
`_locate_and_click_bulk_button()` 側は `TimeoutException` になった
時点（10秒）で即座に諦めて `False` を返していたためである。

v22 では `_locate_and_click_bulk_button()` に `total_timeout`
（既定45秒）を追加し、`TimeoutException` になっても即座には諦めず、
処理中表示が出ていれば「更新して状況を確認する」ボタンを押しながら
`total_timeout` 秒に達するまでポーリングを続けるように変更した。

---------------------------------------------------------------------------
⚠️ v23 変更点（「まとめてアプローチ」ボタンが disabled のまま
             永久に有効化されない不具合の修正 ＝ v22までの根本原因）
---------------------------------------------------------------------------
v22 適用後もなお、2バッチ目で「まとめてアプローチ」ボタンが
`total_timeout`（45秒）待っても見つからず、そのバッチを送信できない
事象が発生した。原因調査のため保存されたデバッグHTMLを確認したところ、
実際には次のことが判明した。

  <button disabled="" class="styles_btnUpload__snR_0 ..."
          data-theme="primary">まとめてアプローチ</button>

ボタン自体はDOM上に常に存在しており、「見つからない」のではなく
`disabled` 属性が付いた状態だった。この disabled は、候補者の
チェックボックスが1件も選択されていない場合に付与される。つまり
v20/v21/v22までの実装は、ボタンが操作不可能になる原因を
「AirWork側が非同期に送信を処理している一時的な状態（処理中表示）」
だとしか想定しておらず、「そもそも選択が反映されていないため
恒久的に disabled のまま」というケースを区別できていなかった。
後者のケースは、どれだけ待っても・どれだけ「更新して状況を確認する」
を押しても解消しない（そもそも処理中表示自体が出ていないため）。

実際に選択が反映されなかった原因ははっきり特定できていないが、
直前バッチの「送信完了」通知表示に伴う非同期の再描画と、次バッチの
チェックボックス選択操作（`_select_all_checkbox()` /
`_select_individual_checkboxes()`）のタイミングが競合し、選択操作が
UIに反映される前に上書きされてしまっている可能性が高い。

v23 では、選択操作の直後に新設の `_wait_for_bulk_button_enabled()`
でボタンの disabled が実際に外れたかを確認し、外れていなければ
選択操作自体をリトライする `_select_candidates_for_batch()` を
`_send_bulk_approach()` に組み込んだ。選択が最終的に反映されなかった
場合は、無意味なボタン探索・送信を試みずにそのバッチで処理を打ち切る
ようにした（結果として目標人数に届かなければ、従来どおり
「確認必要」ステータスとして人手による確認に回る）。

---------------------------------------------------------------------------
⚠️ v24 変更点（v23の根本原因を特定・修正：ページ送り直後の
             ハイドレーション未完了により「すべて選択」クリックが
             無反応になる問題）
---------------------------------------------------------------------------
v23 適用後もなお2バッチ目（ページ送り後の1バッチ目）で選択が
反映されない事象が発生したため、保存されたデバッグHTMLを再調査した。
その結果、以下のことが判明した。

  * デバッグ取得時点で候補者一覧は確かに「2ページ目」
    （`aria-current="true"` が付いたページ番号のリンクが "2"）に
    遷移できていた。すなわち `_go_to_next_candidate_page()` 自体の
    ページ送り動作は正常であり、v22までに疑っていた「同じ候補者を
    再選択しようとして無効化されている」という仮説は誤りだった。

  * 「すべて選択」チェックボックス（`aria-label='isSelectionAll'`）は
    実際には <label> でラップされた、画面上は非表示の <input> に対して
    `execute_script` 経由のJavaScriptクリックを行っていた。この方式は
    要素が見えている場合でも、Reactのイベントハンドラがまだバインド
    されていない「ハイドレーション未完了」のタイミングでは正しく
    処理されないことがある。これは `_click_condition_search_button()`
    で既に対処していたのと同種の Next.js ハイドレーションレース
    コンディションである。

  * 1バッチ目（ページの初回読み込みから、求人検索・条件入力・検索
    実行など複数ステップを経て十分な時間が経過した状態）では問題なく
    機能していたが、ページ送り直後（従来は固定1.2秒しか待っていな
    かった）の2バッチ目以降では、まだハイドレーションが完了して
    いないタイミングでクリックしてしまい、無反応になっていたと
    考えられる。

v24 では以下の2点を修正した。

  1. `_go_to_next_candidate_page()`: ページ送り後の待機を、固定1.2秒
     から document.readyState 待ち＋ハイドレーション猶予＋候補者一覧
     （または空表示メッセージ）が実際に描画されるまでのポーリング
     待ちに強化した。

  2. `_select_all_checkbox()`: 非表示の <input> への JavaScript
     クリックではなく、実際に画面上でクリック可能な <label> に対して
     ActionChains による本物のマウス操作（move_to_element + click）を
     行うように変更した（`_click_condition_search_button()` と同様の
     対策）。ラベルが見つからない、または操作に失敗した場合は、
     従来どおり input への JavaScript クリックにフォールバックする。

  3. 併せて、`_select_candidates_for_batch()` が最終的に選択の反映を
     確認できなかった場合に、原因調査用のデバッグHTML/スクリーン
     ショットを保存するようにした（`_dump_debug_snapshot`）。

---------------------------------------------------------------------------
⚠️ v25 変更点（現在ページの候補者が0件のとき、即座に打ち切らず
             次ページへ遷移して確認するように修正）
---------------------------------------------------------------------------
従来の `_send_bulk_approach()` は、現在ページの候補者数
（`_count_candidates_on_page()`、`_wait_for_candidates_or_empty()` で
描画待ちした後の値）が 0 件だった場合、そのまま `break` して処理全体を
終了していた。

しかし実際の運用では、次のようなケースが起こりうる。
  * ページ送り直後の描画タイミングのブレなどにより、実際には候補者が
    存在するページでも一時的に 0 件と判定されてしまう。
  * 何らかの理由でたまたま現在のページだけ候補者が0件でも、次ページ
    以降にはまだ候補者が残っている可能性がある
    （※通常は検索結果が連番でページ分割されるため稀だが、念のため
      安全側に倒す）。

v25 では、現在ページで 0 件と判定された場合、即座に処理を打ち切るのでは
なく、まず `_go_to_next_candidate_page()` で次ページへの遷移を試みる。
  * 次ページへの遷移に成功した場合（＝「次へ」ボタンがまだ有効だった
    場合）は、ループの先頭に戻って新しいページで候補者数を再判定する。
  * 次ページへの遷移が失敗した場合（＝「次へ」ボタンが disabled、
    つまり最後のページまで確認し終えた場合）は、これ以上探すページが
    無いため、従来どおり `break` して処理を終了する。

これにより、無限ループに陥ることなく（`_go_to_next_candidate_page()`
がページの終端で確実に `False` を返すため）、候補者が見つかるページ
まで安全に探索を続けられるようになった。

---------------------------------------------------------------------------
⚠️ v26 変更点（v23〜v25までの「選択してもボタンが有効にならない」問題の
             真の根本原因を特定・修正：処理中は候補者チェックボックス
             自体が disabled になっている）
---------------------------------------------------------------------------
v23〜v25 を適用してもなお、まれに「チェックボックスを選択しましたが
『まとめてアプローチ』ボタンが有効になりませんでした」という WARN が
出て、そのバッチ（〜そのままそのシート行全体）が「確認必要」に回って
しまう事象が残っていた。原因調査のため保存された
`debug_selection_not_reflected_*.html` / `.png` を確認したところ、
以下のことが判明した。

  * スクリーンショットの時点で、ヘッダー部分にはまだ前バッチの
    「まとめてアプローチを送信中... / 更新して状況を確認する」という
    処理中表示（`styles_processingContainer__...`）が残っていた
    （＝「まとめてアプローチ」ボタン自体がまだ再表示されていない
    状態）。

  * このとき、実HTMLでは「すべて選択」チェックボックスが

      <input data-la="jobseekers_checkbox_all_off_click"
             aria-label="isSelectionAll"
             class="styles_element__PLUni" type="checkbox" disabled>

    のように `disabled` 属性付きになっており、さらに各候補者の
    チェックボックスも

      <input data-la="jobseekers_checkbox_click"
             aria-label="jobseekers_checkbox_click_0"
             disabled class="styles_element__PLUni" type="checkbox"
             value="CAP087487089">

    のように同様に `disabled` になっていた。

  * つまり、AirWork側は前バッチの一括アプローチ処理が完了する
    （＝本物の成功通知が出る）までの間、候補者一覧のチェックボックス
    そのものを丸ごと操作不可にしている。この状態でチェックボックスを
    クリックしても、DOM上は例外なく「クリックできた」ように見える
    （`disabled` 要素への `execute_script` 経由クリックは静かに
    無視される）が、実際には一切選択されない。

  * v23〜v25までの実装は、この現象を「選択操作自体は成功しているが
    UIへの反映（Reactの状態更新）が間に合っていない」ケースとしてしか
    想定しておらず、選択操作をリトライしていた。しかし本当の原因は
    「そもそも操作対象が disabled で無効化されている」ことであり、
    これは選択操作を何度リトライしても解決しない
    （`_click_bulk_approach_button()` 末尾の再表示待ちループが最大
    15秒しかなく、AirWork側の処理がそれより長引いた場合に発生する）。

v26 では、次バッチのチェックボックス選択を始める前に、新設の
`_wait_until_not_processing()` で処理中表示
（`_is_processing()` が True の間）が完全に解消するまで、
「更新して状況を確認する」ボタンを押しながら明示的にポーリングして
待つようにした（最大60秒、2秒間隔。`_read_success_message()` と同様の
ポーリング構造）。処理中表示が消えた後は、チェックボックスの
`disabled` 属性も外れているはずなので、従来どおり
`_select_candidates_for_batch()` で選択・反映確認を行う。
60秒待っても処理中表示が解消しない場合は、無意味な選択リトライを
繰り返さずにそのバッチ送信を打ち切り、「確認必要」として人手による
確認に回すようにした。

---------------------------------------------------------------------------
⚠️ v27 変更点（`_wait()` 全体で StaleElementReferenceException を
             無視してリトライするように変更）
---------------------------------------------------------------------------
実運用ログで、`_click_condition_search_button()` の

    btn = self._wait(15).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., '条件で候補者を探す')]")
        )
    )

にて `selenium.common.exceptions.StaleElementReferenceException` が
発生し、その行の処理全体が失敗するケースが確認された（行171）。

  File "selenium\\webdriver\\support\\wait.py", line 112, in until
  File "selenium\\webdriver\\support\\expected_conditions.py", line 223,
       in _element_if_visible
  File "selenium\\webdriver\\remote\\webelement.py", line 308, in is_displayed
  selenium.common.exceptions.StaleElementReferenceException

原因は、`WebDriverWait.until()` の1回のポーリング内で「要素を
locate → is_displayed() を呼ぶ」間にReactが再描画し、取得した
`WebElement` が古くなる（stale になる）Next.js のハイドレーション
未完了レースコンディションである。`WebDriverWait` は既定では
`NoSuchElementException` のみを無視してリトライするため、
`StaleElementReferenceException` はそのまま呼び出し元まで伝播し、
`_apply_conditions` → `_process_row` を経て行全体の処理が
`except Exception` で失敗扱いになっていた（v21で「まとめてアプローチ」
ボタンについては個別に対処済みだったが、`_click_condition_search_button`
を含む他の `self._wait(...)` 呼び出しは無防備なままだった）。

v27 では、共通ヘルパー `_wait()` の `WebDriverWait` に
`ignored_exceptions=(StaleElementReferenceException,)` を追加した。
これにより、`EC.element_to_be_clickable` 等の待機中に
`StaleElementReferenceException` が発生しても即座に失敗とせず、
timeout に達するまで要素を再locateしながらリトライするようになった
（`EC.element_to_be_clickable` は毎回要素を再locateするため、stale
状態のまま使い続けることはない）。ファイル内のほぼ全ての待機処理が
`self._wait(...)` 経由のため、`_click_condition_search_button()` を
含む多くの箇所でこの種のレースコンディションに対して個別対応せずに
まとめて頑健になる。

---------------------------------------------------------------------------
⚠️ v28 変更点（シート書き込みリトライ／実選択数の反映／その他の頑健化）
---------------------------------------------------------------------------
コードレビューで見つかった以下の点を修正した。

  1. 【重要度: 高】Google Sheets への書き込み（ステータス／ログイン日時／
     送信人数）が失敗した場合、従来は ERROR ログを出すだけで処理には
     一切影響させていなかった。特に「実際にアプローチを送信した後に
     ステータスを『対応済み』へ更新する」書き込みが失敗すると、次回
     実行時にその行が再び「対応必要」として処理され、同じ候補者へ
     重複してアプローチを送信してしまうリスクがあった。
     → 新設の `_write_cell_with_retry()` で指数バックオフ付き最大5回の
       リトライを行うようにした。それでも失敗した場合、実際に送信が
       完了していた場合は「★重要」という目立つERRORログで手動確認を
       強く促すようにした（`_process_row()` 内）。

  2. 【重要度: 中】`_select_candidates_for_batch()` は「1ページ=50件」
     という前提のもとで送信人数（take）を事前に見積もっていたが、
     `_select_all_checkbox()` は実際に画面に表示されている候補者を
     "全員" 選択するため、この前提が崩れた場合（ページ表示件数が
     50件を超える等）、実際にAirWorkへ送信される人数と bot が記録する
     `total_sent` が食い違う可能性があった。
     → 新設の `_count_checked_candidate_checkboxes()` で実際に
       チェック状態になっている件数をDOMから数え、見積もり値と
       食い違う場合は実際の値を使うように変更した。

  3. 【重要度: 低】`_process_row()` で「候補者を探す」クリック後に
     固定 `sleep(1.5)` のみで候補者一覧の描画完了を待っていたため、
     タイミング次第で0件と誤判定し、無条件検索フォールバックが
     不要に発動することがあった。他の待機処理と同様に
     document.readyState 待ちを追加した。

  4. 【重要度: 低】求人番号などシート由来の値をXPathへ埋め込む際、
     シングルクォートのエスケープを行っていなかった。新設の
     `_xpath_literal()` でエスケープしてから埋め込むように統一した。

  5. `_locate_and_click_bulk_button()` の未使用引数 `max_attempts` を
     削除した（実際には `total_timeout` のみでリトライ回数を制御して
     おり、`max_attempts` は一度も参照されていなかった）。

---------------------------------------------------------------------------
⚠️ v29 変更点（確認必要への更新時に具体的な理由をステータス列に併記／
             求人ID検索のtd判定を子要素まで含めて正規化）
---------------------------------------------------------------------------
コードレビューで見つかった以下の点を修正した。

  1. 従来、「確認必要」（STATUS_NEED_CONFIRM）に更新される複数の
     分岐（掲載状況確認／条件反映チェック／無条件検索フォールバック／
     送信人数不足）はすべて同じ固定文字列を書き込むだけで、シートを
     見ただけではどこで何が原因で止まったのかが分からなかった。
     v29 では `_update_status_with_reason()` を新設し、「確認必要」に
     更新する4箇所すべてで、原因（理由）をステータスセルに
     「確認必要（理由）」の形式で併記するようにした。
     これにより、ユーザーはシートを見るだけでどの工程で何が起きたのか
     を把握できるようになる。

     併せて、STATUS_NEED_CONFIRM の元の意味が2つ混在していた点も修正
     した。従来 `_check_job_offer_publish_status()` は「掲載状況が
     読み取れなかった場合」も「掲載中だった場合」もどちらも文字列
     "確認必要" を返しており、呼び出し側でこの2つを区別できなかった。
     v29 では読み取れなかった場合は None を返すように変更し、
     呼び出し側でどちらのケースかをログ・理由に明示できるようにした。

  2. 求人番号が実際にはAirWork上に存在するにもかかわらず、bot が
     「求人ID見つからない」と誤判定する事例が確認された。原因調査の
     結果、候補者ページの求人一覧テーブルで求人番号を検索する際の
     XPath が `td[normalize-space(text())=...]` となっており、これは
     `<td>` 直下のテキストノードのみを対象とする（`<td><span>1234567
     </span></td>` のように子要素にテキストが入っている場合は一致しない）
     ことが判明した。v29 では `normalize-space(.)`（`<td>` 配下の
     テキストを子要素も含めて連結したもの）で判定するように修正した。
     また、シート側の求人番号に全角数字・前後の空白・ゼロ幅スペース等の
     不可視文字が混入していても正しく一致するよう `_normalize_job_id()`
     を新設し、`_process_row()` で読み込み時に適用するようにした。
     見つからなかった場合は調査用にデバッグHTML/スクリーンショットを
     保存するようにした。

---------------------------------------------------------------------------
⚠️ v47 変更点（一括アプローチ「アプローチを送る」ボタンが押せなかった
             場合、送信済みとして誤カウントしていた重大バグの修正）
---------------------------------------------------------------------------
コードレビューで、`_click_bulk_approach_button()` に次の重大な不具合が
見つかったため修正した。

  従来のコード:

      if not self._click_confirm_send_button(timeout=10.0):
          self._log(
              "確認ダイアログの「アプローチを送る」ボタンが見つかりません"
              "でした。実際には送信が確定していない可能性があります。"
              "AirWork上で確認画面が表示されているか確認してください。",
              "WARN",
          )
          return True   # ← ここが問題

  「N人にまとめてアプローチ」ボタンをクリックして確認ダイアログを
  開く（手順1）ところまでは成功しても、実際に送信を確定させる
  「アプローチを送る」ボタン（手順2、`_click_confirm_send_button()`）
  のクリックに失敗した場合、実際には何も送信されていないにも
  かかわらず、本メソッドは `True`（＝成功）を返していた。

  この戻り値は呼び出し元の `_send_bulk_approach()` でそのまま使われる:

      if self._click_bulk_approach_button():
          total_sent += take
          remaining -= take

  そのため、実際には未送信のバッチの人数（take）が `total_sent` に
  加算されてしまい、結果的に `sent >= limit` と判定されて
  `_process_row()` がその行を「対応済み」（STATUS_DONE）として確定
  させてしまう可能性があった。これは v15〜v26 まで一貫して追求してきた
  「AirWork側の本物の成功通知が確認できて初めて送信済みとみなす」
  という設計方針に反しており、実際には送信していないのに送信済みと
  誤記録する、最も避けるべき種類のバグだった。

  さらに、この誤ったカウントは `_record_result()` 経由で
  `sent_count` としても記録されるため、
  `_revert_interrupted_need_confirm_rows()` の「一部でも送信済みの
  行は自動的に『対応必要』へ戻さない」という安全策（v43）にも
  誤って引っかかり、問題の発覚をさらに遅らせる可能性があった。

  v47 では、「アプローチを送る」ボタンをクリックできなかった場合は
  `False` を返すように修正した。これにより:
    * `_send_bulk_approach()` はこのバッチを `total_sent` に加算せず、
      `self._last_bulk_issue` に理由を残してバッチ送信を打ち切る。
    * `_process_row()` は `sent < limit` と正しく判定し、その行を
      「確認必要」として理由付きで人手の確認に回す（誤って
      「対応済み」にすることはなくなる）。
  ログレベルも WARN から ERROR に引き上げ、この状況がより目立つように
  した。
===========================================================================
"""

import glob
import json
import os
import queue
import re
import sys
import threading
import time
import traceback
from collections import defaultdict
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import gspread
from google.oauth2.service_account import Credentials

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)

# ★ v2: ログイン／ブラウザ起動は bot_core.AirWorkBotBase に委譲する。
from bot_core import AirWorkBotBase
from config_loader import ConfigLoader

# ★ v30: 重大エラー／実行サマリーをChatworkへ通知する。
from chatwork_notifier import ChatworkNotifier

# ═══════════════════════════════════════════════════════════════════════
#  定数
# ═══════════════════════════════════════════════════════════════════════

# 「手動アプローチ」タブは他のタブと異なり、⚙️設定タブのスプレッドシートではなく
# 専用の固定スプレッドシートを使用する。
# ⚠️ TODO: 実際に使用するスプレッドシート ID に書き換えてください。
#          （URL の https://docs.google.com/spreadsheets/d/【ここ】/edit の部分）
MANUAL_APPROACH_SHEET_ID = "1NfmnDiPKcnLlhqld_oCOYTYCgAz-m8sL5vujbE4OVU8"
MANUAL_APPROACH_SHEET_URL = (
    f"https://docs.google.com/spreadsheets/d/{MANUAL_APPROACH_SHEET_ID}/edit"
)

CANDIDATES_URL = "https://ats.rct.airwork.net/candidates"
JOB_OFFERS_URL = "https://ats.rct.airwork.net/job_offers?currentPage=1&pageSize=50"

# 対象シートの列（0-indexed。get_all_values() の行リストに対応）
COL_STATUS  = 0   # A
COL_COMPANY = 1   # B
COL_AIRID   = 3   # D
COL_PASS    = 4   # E
COL_JOBID   = 5   # F
COL_LIMIT   = 6   # G
COL_H       = 7   # H 希望勤務地
COL_I       = 8   # I 最終学歴
COL_J       = 9   # J 年以降
COL_K       = 10  # K 年以前
COL_L       = 11  # L 年齢下限
COL_M       = 12  # M 年齢上限
COL_N       = 13  # N スキル
COL_O       = 14  # O 経験
COL_P       = 15  # P 保有資格
COL_Q       = 16  # Q 英会話レベル
COL_LOGIN_TIME = 18  # S
COL_SENT_COUNT = 19  # T

STATUS_NEED           = "対応必要"
STATUS_DONE            = "対応済み"
STATUS_JOB_NOT_FOUND   = "求人ID見つからない"
STATUS_NOT_FULLTIME    = "正社員以外"
STATUS_UNPUBLISHED     = "未掲載"
STATUS_NEED_CONFIRM    = "確認必要"
# ★ v7: 検索条件に合致する候補者がいない／アプローチ上限に達している場合の
#   空表示メッセージを検知したときに設定するステータス。
# ★ v35: 上記の空表示メッセージはAirWork側で「条件に合致する候補者が
#   いない」ケースと「手動アプローチの上限（1社1日500人）に達した」
#   ケースを区別せず同じ文言で表示するため、従来はこの2つを
#   STATUS_NO_CANDIDATES に一括して倒していた。
#   しかし運用上、この2つは原因も対応方法も全く異なる
#  （前者はデータ側の問題、後者は単に「今日はもう送れる上限に達した
#   だけ」で翌日には自然に再開できる）ため、区別できるようにした。
#   AirWorkのUI自体には1日の累計送信人数が集計表示されないため、
#   bot側でシートの記録（同じAirIDの当日分T列の合計）から自前で
#   500人に達しているかどうかを判定する（`_get_company_sent_total_today`
#   を参照）。
#     - 累計が500人未満 → 本当に条件に合う候補者がいない
#       → STATUS_NO_MATCHING_CANDIDATES
#     - 累計が500人以上 → 1日の上限に達している
#       → STATUS_NO_CANDIDATES（従来どおり）
#   なお、「候補者を探す」ボタンが操作不可＋掲載中の状態が自動リトライ
#   上限まで解消しなかった場合（v33で追加した別経路）は、この上限判定とは
#   無関係の問題のため、常に STATUS_NO_CANDIDATES のまま変更しない。
STATUS_NO_CANDIDATES   = "候補者を表示できません"
STATUS_NO_MATCHING_CANDIDATES = "条件に合う候補者がいない"

# 1社（AirID）が1日に手動アプローチを送信できる人数の上限。
# AirWork側のUIには累計送信人数が表示されないため、bot が自前で
# シートの記録から計算して判定するために使う。
DAILY_APPROACH_LIMIT_PER_COMPANY = 500

# ─────────────────────────────────────────────────────────────────────
#  ★ v31: 自動リトライ設定
# ─────────────────────────────────────────────────────────────────────
# 「確認必要」になった行は、AirWork側の一時的な処理中状態（非同期送信の
# 遅延、UI描画タイミングのズレ等）が原因であるケースが多く、単純に
# もう一度処理し直すだけで解消することが少なくない。
# Chatworkへ最終報告する前に、同一 run() 内で自動的にリトライし、
# 「本当に人手の確認が必要な行」だけを最終報告に残すことで、
# 一時的な問題を毎回サポートに報告してしまう"誤報"を減らす。
#
# 「求人ID見つからない」「未掲載」「正社員以外」「候補者を表示できません」は
# データ・掲載状況そのものに起因する構造的な結果であり、何度リトライしても
# 結果は変わらないため、自動リトライの対象には含めない
#（＝STATUS_NEED_CONFIRM の行のみリトライする）。
RETRY_MAX_ATTEMPTS = 2          # 初回1回 + 自動リトライ1回（既定）
RETRY_WAIT_SECONDS = 10.0       # リトライ前に一時的な状態の解消を待つ秒数

# ─────────────────────────────────────────────────────────────────────
#  「条件で候補者を探す」モーダル内の実HTMLに基づく対応表（v3で追加）
# ─────────────────────────────────────────────────────────────────────

# 最終学歴: シート上の表示テキスト → <input type="checkbox" name="コード">
#   実HTML: <input name="1"> ... <span>大学院（博士）</span>  のように
#   input の name 属性が学歴コードそのものになっている。
EDUCATION_LEVEL_CODE_MAP: Dict[str, str] = {
    "大学院（博士）": "1",
    "大学院（修士）": "2",
    "大学院（MBA/MOT）": "3",
    "大学院（法科）": "4",
    "大学院（その他専門職）": "5",
    "4年制大学": "6",
    "6年制大学": "7",
    "専門職大学": "8",
    "専門職短期大学": "9",
    "高等専門学校": "10",
    "短期大学": "11",
    "専門学校": "12",
    "高等学校": "13",
    "その他": "14",
}

# 英会話レベル: シート上の表示テキスト → <select name="candidateFilter.englishLevelId">
#   の <option value="コード">
ENGLISH_LEVEL_VALUE_MAP: Dict[str, str] = {
    "指定なし": "1",
    "簡単な会話が可能": "5",
    "日常会話が可能": "4",
    "ビジネス会話が可能": "3",
    "ネイティブレベルで会話可能": "2",
}

# 既存プロジェクトのサービスアカウント json のパス。
# ここに直接パスを書いてもよいが、既定では下の _find_service_account_file()
# が自動的に探すため、通常は空のままで OK。
SERVICE_ACCOUNT_FILE = ""
GSPREAD_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# ★ v29: 求人番号の正規化に使う全角/半角数字の対応表
_FULLWIDTH_DIGITS = "０１２３４５６７８９"
_HALFWIDTH_DIGITS = "0123456789"


def _find_service_account_file() -> str:
    """
    Google サービスアカウントの認証用 JSON ファイルを探す。
    優先順位:
      1) SERVICE_ACCOUNT_FILE 定数に明示的にパスが書かれていればそれを使う
      2) 環境変数 GOOGLE_APPLICATION_CREDENTIALS / GSPREAD_CREDENTIALS_FILE
      3) 実行フォルダ（exe/py と同じ場所）・カレントフォルダにある
         よくある名前の json ファイル
      4) 上記フォルダ内の *.json を中身から判定
         （"type": "service_account" を含むもの）
    """
    if SERVICE_ACCOUNT_FILE and os.path.isfile(SERVICE_ACCOUNT_FILE):
        return SERVICE_ACCOUNT_FILE

    env_path = (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or os.environ.get("GSPREAD_CREDENTIALS_FILE")
    )
    if env_path and os.path.isfile(env_path):
        return env_path

    base_dirs = []
    try:
        base_dirs.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    except Exception:
        pass
    base_dirs.append(os.path.dirname(os.path.abspath(__file__)))
    base_dirs.append(os.getcwd())
    # 重複除去（順序維持）
    base_dirs = list(dict.fromkeys(d for d in base_dirs if d))

    common_names = [
        "service_account.json",
        "credentials.json",
        "gcp_service_account.json",
        "google_credentials.json",
        "google-credentials.json",
        "sa_key.json",
        "client_secret.json",
    ]
    for d in base_dirs:
        for name in common_names:
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p

    for d in base_dirs:
        for p in glob.glob(os.path.join(d, "*.json")):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if (
                    isinstance(data, dict)
                    and data.get("type") == "service_account"
                    and "private_key" in data
                    and "client_email" in data
                ):
                    return p
            except Exception:
                continue

    raise RuntimeError(
        "Google サービスアカウントの認証ファイル (.json) が見つかりません。\n"
        "次のいずれかで対応してください:\n"
        "  1) このツールの exe/py と同じフォルダにサービスアカウントの\n"
        "     JSON キーファイルを置く（例: service_account.json）\n"
        "  2) 環境変数 GOOGLE_APPLICATION_CREDENTIALS にファイルパスを設定する\n"
        "  3) airwork_manual_approach.py 冒頭の SERVICE_ACCOUNT_FILE 定数に\n"
        "     直接パスを書く"
    )


def _col(row: List[str], idx: int) -> str:
    """行データから安全に列の値（文字列/strip 済み）を取得する。"""
    if idx < len(row):
        return (row[idx] or "").strip()
    return ""


def _xpath_literal(value: str) -> str:
    """
    ★ v28で追加。
    XPath の文字列リテラルとして安全に埋め込めるようにエスケープする。

    従来、求人番号（job_id）は f"//td[normalize-space(text())='{job_id}']"
    のように単純に '...' で囲んでXPathへ埋め込んでいた。求人番号は
    通常は数字のみのため実害は出ていなかったが、シート側の値に
    シングルクォート（'）が含まれていた場合、生成されるXPathの構文が
    壊れて NoSuchElementException や意図しないマッチになる可能性が
    あった。

    XPath 1.0 には文字列リテラル用のエスケープ構文が無いため、
    値に ' と " が両方含まれるケースは concat() で分割して組み立てる
    （XPathでの一般的な回避策）。
    """
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"


def _normalize_job_id(value: str) -> str:
    """
    ★ v29で追加。
    シート側の求人番号（F列）を正規化する。

    実際の運用で、求人番号がAirWork上には確かに存在するにもかかわらず、
    bot が「求人ID見つからない」と誤判定する事例が確認された。原因として、
    シート側の値に次のようなコピペ起因のズレが混入しているケースが
    考えられる。

      * 全角数字（例: "１２３４５６７"）で入力されている
      * 前後に半角/全角スペースが付いている
      * Excel/Sheets からのコピペで、ゼロ幅スペースや BOM 等の
        見た目には分からない不可視文字が混入している

    これらはいずれも通常の文字列完全一致では候補者ページ側の表示
    （半角数字のみ）と一致しないため、実際には存在する求人番号でも
    「見つからない」と誤判定されてしまう。
    本関数は全角数字を半角に変換し、代表的な不可視文字を除去した上で
    前後の空白をトリムする。
    """
    if not value:
        return ""
    v = value.strip()
    v = v.translate(str.maketrans(_FULLWIDTH_DIGITS, _HALFWIDTH_DIGITS))
    # ゼロ幅スペース(U+200B〜200D)、BOM(U+FEFF)、全角スペース(U+3000)を除去
    v = re.sub(r"[\u200b\u200c\u200d\ufeff\u3000]", "", v)
    return v.strip()


def extract_sheet_id(value: str) -> str:
    """
    ★ v41で追加。
    GUIで処理対象スプレッドシートをユーザーが自由に設定できるように
    した際、Googleスプレッドシートの共有URL全体
    （例: https://docs.google.com/spreadsheets/d/【ID】/edit#gid=0）を
    そのまま貼り付けても、素のスプレッドシートID部分だけを貼り付けても
    どちらでも動作するように正規化するためのヘルパー。

    URLパターンに一致すれば "/d/" と次の "/" の間のID部分を抽出して
    返す。一致しなければ、入力値をIDそのものとみなしてそのまま
    （前後の空白を除去して）返す。
    """
    value = (value or "").strip()
    if not value:
        return ""
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", value)
    if m:
        return m.group(1)
    return value


class AirWorkManualApproach:
    """手動アプローチタブの自動化本体。"""

    def __init__(
        self,
        target_sheet_id: Optional[str] = None,
        target_tab_name: Optional[str] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
        headless: bool = True,
        config_loader: Optional[ConfigLoader] = None,
    ):
        """
        Parameters
        ----------
        target_sheet_id : str, optional
            処理対象スプレッドシートの ID。省略時はファイル上部で固定された
            `MANUAL_APPROACH_SHEET_ID` を使用する（このタブは他タブと違い、
            ⚙️設定タブのスプレッドシートは使わない）。
            URL全体を渡された場合は `extract_sheet_id()` で呼び出し側が
            IDを抽出しておくことを想定しているが、万一URLがそのまま
            渡された場合でも `_open_target_worksheet()` 側で再度
            正規化を試みる。
        target_tab_name : str, optional
            ★ v41で追加。処理対象スプレッドシート内の特定のタブ（シート）
            名を指定する。省略時（None または空文字）は、従来どおり
            スプレッドシートの先頭タブ（`ss.sheet1`）を使用する。
            GUIでユーザーがタブ名を指定できるようにするために追加した。
        log_callback : Callable[[str, str], None]
            (message, level) を受け取るログ関数。level は
            "INFO"/"WARN"/"ERROR"/"OK"。
        headless : bool
            True ならヘッドレスでブラウザを起動。
        config_loader : ConfigLoader, optional
            ブラウザ起動・ログインを委譲する bot_core.AirWorkBotBase の
            必須引数。GUI 側で既に生成済みのインスタンスがあればそれを渡す
            こと（Config タブの読み込みを二重にしないため）。省略した場合は
            このファイル内でデフォルトのインスタンスを生成する（このタブは
            Config タブの列定義を使わないため、動作に支障はない）。
        """
        self.target_sheet_id = (target_sheet_id or MANUAL_APPROACH_SHEET_ID).strip()
        self.target_tab_name = (target_tab_name or "").strip()
        self.log_callback = log_callback
        self.headless = headless

        self._config_loader = config_loader or self._make_default_config_loader()

        # ★ v2: 自前でSeleniumドライバを管理せず、bot_core.AirWorkBotBase の
        #   インスタンスに委譲する（ログイン処理も含む）。
        self._bot: Optional[AirWorkBotBase] = None

        self.gc: Optional[gspread.Client] = None
        self.target_ws = None

        self._stop_flag = False
        self._current_air_id: Optional[str] = None
        self._keep_alive = False  # True の場合、close() してもドライバを維持

        # ★ v29: 「確認必要」に更新する直前に、直近で発生した具体的な
        #   原因（理由）を一時的に保持しておくための変数。
        #   `_update_status_with_reason()` でステータスセルに併記する。
        self._last_condition_issue: str = ""
        self._last_bulk_issue: str = ""

        # ★ v30: Chatwork通知。設定ファイル未整備でも例外にならず、
        #   通知機能のみ自動的に無効化される（bot本体は通常どおり動作する）。
        self._notifier = ChatworkNotifier(log_callback=log_callback)
        self._run_stats: Dict[str, object] = self._new_run_stats()
        # ★ v40で追加。GUIの preview_report_text() / send_report() が
        #   「プレビューで見せた内容」と「実際に送信する内容」を完全に
        #   一致させるためのキャッシュ。
        self._last_report_body: Optional[str] = None

    # ─────────────────────────────────────────────────────────────
    #  driver は bot_core.AirWorkBotBase 側が保持する。
    #  このクラスの他のメソッド（候補者検索・条件入力など）は今までどおり
    #  self.driver 経由で Selenium を直接操作するので、プロパティとして
    #  委譲する。
    # ─────────────────────────────────────────────────────────────
    @property
    def driver(self) -> Optional[webdriver.Chrome]:
        return self._bot.driver if self._bot is not None else None

    @property
    def current_sheet_url(self) -> str:
        """
        ★ v41で追加。
        Chatworkへの報告・エラー通知に載せるスプレッドシートのリンクは、
        従来ファイル冒頭で固定された `MANUAL_APPROACH_SHEET_URL` を
        常に使っていた。しかしGUIからユーザーが処理対象シートを変更
        できるようになったため、実際に処理中の `self.target_sheet_id`
        から動的にURLを組み立てて返すようにした。
        """
        return f"https://docs.google.com/spreadsheets/d/{self.target_sheet_id}/edit"

    def _make_default_config_loader(self) -> ConfigLoader:
        """
        bot_core.AirWorkBotBase は config_loader を必須引数として要求する。
        GUI 側から既存インスタンスが渡されなかった場合はここで生成する。
        このタブでは Config タブの列定義（file_cfg.col() など）を一切
        参照しないため、ConfigLoader の内部実装に関わらず
        _login()/_launch_browser() の動作には影響しない。
        """
        try:
            return ConfigLoader()
        except Exception as e:
            raise RuntimeError(
                "ConfigLoader の初期化に失敗しました。GUI 側で既に生成済みの "
                "ConfigLoader インスタンスを "
                "AirWorkManualApproach(config_loader=...) として渡してください。"
            ) from e

    # ─────────────────────────────────────────────────────────────
    #  外部制御
    # ─────────────────────────────────────────────────────────────
    def stop(self):
        self._stop_flag = True
        if self._bot is not None:
            self._bot.stop()

    def _stopped(self) -> bool:
        return self._stop_flag

    def close(self):
        if self._keep_alive:
            return
        if self._bot is not None and self._bot.driver is not None:
            # ★ v39: driver.quit() がChromeプロセスの応答なしにより
            #   無期限にブロックしてしまうケースへの対策。タイムアウト
            #   ガード経由で呼び出し、既定20秒で諦めて処理を先に進める
            #   （ブラウザプロセスがゾンビ化する可能性は残るが、bot
            #   全体が永久にフリーズするよりはるかに良い）。
            self._run_with_timeout(
                self._bot.driver.quit,
                timeout=20.0,
                description="ブラウザの終了処理（driver.quit）",
            )
            self._bot.driver = None

    def _log(self, msg: str, level: str = "INFO"):
        if self.log_callback:
            try:
                self.log_callback(msg, level)
            except Exception:
                print(f"[{level}] {msg}")
        else:
            print(f"[{level}] {msg}")

    # ─────────────────────────────────────────────────────────────
    #  ★ v39: ネットワーク呼び出し（Google Sheets API・Chrome終了処理等）が
    #  無期限にハングするのを防ぐための汎用タイムアウトガード
    # ─────────────────────────────────────────────────────────────
    def _run_with_timeout(
        self,
        func: Callable,
        timeout: float,
        description: str,
        default=None,
    ):
        """
        ★ v39で追加、v44・v45で修正。
        実運用で、全行の処理が完了した後（Chatworkへのサマリー通知や
        シートの最終集計、ブラウザの終了処理あたり）で bot がフリーズ
        したまま応答しなくなる事象が報告された。

        原因として最も疑わしいのは、`gspread`（Google Sheets API
        クライアント）や Selenium の `driver.quit()` の呼び出しに
        タイムアウトが設定されておらず、ネットワークが不安定になったり
        Chromeプロセスが応答しなくなったりした場合、これらの呼び出しが
        戻ってこなくなる（＝プログラム全体がそこで永久に止まる）ことで
        ある。この状態になると、停止フラグ（`self._stop_flag`）は
        あくまで「呼び出しとその次の呼び出しの間」でチェックされる
        だけの仕組みのため、既にブロックしている最中の呼び出し自体を
        途中で中断することはできず、「停止ボタンを押しても反応しない」
        という状況になる。

        Pythonのスレッドは強制終了できないため、根本的にブロッキング
        呼び出しを完全に中断することはできない。しかし、別スレッドで
        呼び出しを実行し、メインスレッド側は `timeout` 秒だけ待って
        それでも終わらなければ諦めて `default` を返す、という形にする
        ことで、少なくとも「メインの処理フロー全体が無期限に固まる」
        ことは避けられる。

        戻り値: `func()` の戻り値。timeout以内に終わらなければ
                `default`（既定 None）を返す。

        ★ v44で判明した重大なバグ（`ThreadPoolExecutor` 版）:
        当初の実装は `with ThreadPoolExecutor(...) as executor:` を
        使っており、これが実質的にタイムアウトガードとして機能して
        いなかった。`with` ブロックを抜ける際、Pythonは必ず
        コンテキストマネージャの `__exit__` を呼び出す。
        `ThreadPoolExecutor.__exit__` は内部で `self.shutdown(wait=True)`
        を呼ぶため、`future.result(timeout=...)` が `TimeoutError` を
        送出した後でも、`with` ブロックを抜けようとした瞬間に
        `shutdown(wait=True)` が実行され、結局ハングしたままの `func()`
        が実際に終わるまで戻ってこなくなっていた。

        ★ v45で判明した、v44修正でも残っていた根本原因（同じく
        `ThreadPoolExecutor` 起因）:
        v44では `with` をやめ、明示的に `executor.shutdown(wait=False)`
        を呼ぶように変更したが、これでもなお不十分だった。
        `concurrent.futures.thread` モジュールは、Pythonインタプリタの
        終了時に**モジュールレベルで登録された `atexit` フック**
        （`_python_exit`）を持っており、これは「今まさに存在する
        すべての `ThreadPoolExecutor` のワーカースレッド」を、個々の
        executor で `shutdown(wait=False)` を呼んでいたかどうかに
        関わらず、インタプリタ終了時に強制的に `join()` して待ち受ける。
        つまり、GUIアプリを閉じようとした際やスクリプトが終了しようと
        した際に、ハングしたままバックグラウンドに残っている
        ワーカースレッドのせいで、プロセス全体の終了そのものが
        ブロックされてしまう（タスクマネージャーにプロセスが残り続ける
        等）。検証用のミニマル再現コードで、`ThreadPoolExecutor` 版は
        タイムアウト自体は正しく検出できるにもかかわらず、スクリプト
        終了時に固まることを確認済み。

        v45では `ThreadPoolExecutor` を使うのをやめ、
        `threading.Thread(daemon=True)` ＋ `queue.Queue` による実装に
        変更した。デーモンスレッドは `concurrent.futures.thread` の
        atexitフックに一切登録されず、Pythonインタプリタは終了時に
        デーモンスレッドを待たずに強制的に道連れ終了させる。これにより、
        ハングした呼び出し自体を完全に中断することはできない
        （Pythonの原理的な制約）ものの、
          (a) `_run_with_timeout()` の呼び出し元は timeout 秒で
              確実に制御を取り戻せる
          (b) アプリ・スクリプト自体の終了時にも道連れで固まらない
        の両方が保証されるようになった。
        """
        result_box: "queue.Queue" = queue.Queue(maxsize=1)

        def _worker():
            try:
                result_box.put(("ok", func()))
            except Exception as e:
                result_box.put(("error", e))

        # daemon=True が本修正の要。concurrent.futures.ThreadPoolExecutor
        # のワーカースレッドとは異なり、デーモンスレッドはインタプリタ
        # 終了時に join 待ちされることなく道連れで終了する。
        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        try:
            kind, value = result_box.get(timeout=timeout)
        except queue.Empty:
            self._log(
                f"{description}が{timeout:.0f}秒以内に完了しませんでした"
                "（ネットワーク不調またはブラウザの応答なしの可能性があります）。"
                "これ以上待たずに処理を続行します。",
                "WARN",
            )
            return default

        if kind == "error":
            self._log(f"{description}中にエラーが発生しました: {value}", "WARN")
            return default
        return value

    # ─────────────────────────────────────────────────────────────
    #  ★ v30: Chatwork通知用の集計ヘルパー
    # ─────────────────────────────────────────────────────────────
    def _new_run_stats(self) -> Dict[str, object]:
        """
        run() 1回分の実行結果を集計するための入れ物。
        run() の先頭でリセットし、_process_row() の各終端で
        `_record_result()` により更新、run() の finally で
        Chatworkへのサマリー通知に使う。

        ★ v31: `row_results` を「行ごとに1つの最新結果を持つ辞書」に変更した
        （row_idx -> {"status","company","job_id","reason"}）。
        従来は確認必要になった行を単純にリストへ追記していたため、
        自動リトライを導入すると同じ行が複数回記録され、Chatworkへの
        報告が重複・不正確になってしまう。辞書にして row_idx をキーに
        上書きすることで、最終的な（＝最後に試した）結果だけが残るように
        した。
        """
        return {
            "total": 0,
            "row_results": {},   # row_idx -> {"status","company","job_id","reason"}
        }

    def _record_result(
        self,
        status: str,
        row_idx: int,
        company: str,
        job_id: str,
        reason: str = "",
        attempt: int = 0,
        sent_count: int = 0,
    ):
        """
        ★ v30で追加、v31で更新、v42で `attempt` を追加、v43で
        `sent_count` を追加。
        _process_row() が各行の処理を終える直前（ステータス確定時）に
        呼び出し、run() 終了後にChatworkへ送るサマリー通知用の統計を
        更新する。シートへの実際の書き込み成否には関わらず、bot が
        「最終的にどのステータスに倒したか」を記録する。

        同じ row_idx で複数回呼ばれた場合（＝自動リトライで再処理された
        場合）は上書きされ、最後の結果だけが残る。

        `attempt` は、この結果が何回目の試行で確定したものかを記録する
        （1=初回、2以上=自動リトライ）。

        `sent_count` は、この行の処理で実際にAirWorkへ送信できたと
        確認された人数（`_send_bulk_approach()` の戻り値）。0より大きい
        場合、その行は「一部だけでも実際に送信済み」であることを意味する。
        `_revert_interrupted_need_confirm_rows()` はこの値を見て、
        一部でも送信済みの行を「対応必要」へ自動的に戻さないようにする
        （そのまま自動で戻すと、次回実行時に同じ求人へ改めて
        `_send_bulk_approach()` が呼ばれ、既に送信済みの人数分を考慮せず
        G列の上限数までフルに再送信してしまい、結果的に候補者への
        重複アプローチや、意図した上限を超えた送信につながる恐れが
        あるため）。
        """
        self._run_stats["row_results"][row_idx] = {
            "status": status,
            "company": company,
            "job_id": job_id,
            "reason": reason,
            "attempt": attempt,
            "sent_count": sent_count,
        }

    # ─────────────────────────────────────────────────────────────
    #  Google Sheets
    # ─────────────────────────────────────────────────────────────
    def _get_gspread_client(self) -> gspread.Client:
        if self.gc is not None:
            return self.gc
        cred_file = _find_service_account_file()
        self._log(f"認証ファイル: {cred_file}", "INFO")
        creds = Credentials.from_service_account_file(
            cred_file, scopes=GSPREAD_SCOPES
        )
        self.gc = gspread.authorize(creds)
        return self.gc

    def _open_target_worksheet(self):
        """
        固定の `target_sheet_id`（= 既定では MANUAL_APPROACH_SHEET_ID）を
        直接開く。このタブは他のタブと違い、⚙️設定タブのスプレッドシートは
        一切参照しない。

        ★ v41: `self.target_tab_name` が指定されている場合は、そのタブ名
        のワークシートを開く。未指定（空文字）の場合は従来どおり先頭タブ
        （`ss.sheet1`）を使用する。
        """
        if not self.target_sheet_id or self.target_sheet_id == "PUT_YOUR_SHEET_ID_HERE":
            raise RuntimeError(
                "手動アプローチ用のスプレッドシート ID が未設定です。"
                "airwork_manual_approach.py 冒頭の MANUAL_APPROACH_SHEET_ID を"
                "設定してください。"
            )
        # ★ v41: GUI等からURLがそのまま渡された場合の保険として、
        #   ここでも念のため extract_sheet_id() を通す（IDそのものが
        #   渡された場合は無変換で返る）。
        self.target_sheet_id = extract_sheet_id(self.target_sheet_id)

        self._log(f"対象スプレッドシート ID: {self.target_sheet_id}", "OK")
        gc = self._get_gspread_client()
        # ★ v39: gc.open_by_key() がネットワーク不調で無期限にブロック
        #   するのを防ぐ。
        ss = self._run_with_timeout(
            lambda: gc.open_by_key(self.target_sheet_id),
            timeout=30.0,
            description="スプレッドシートを開く処理（open_by_key）",
        )
        if ss is None:
            raise RuntimeError(
                "スプレッドシートを開けませんでした"
                "（タイムアウト、またはネットワークエラーの可能性があります）。"
            )

        if self.target_tab_name:
            ws = self._run_with_timeout(
                lambda: ss.worksheet(self.target_tab_name),
                timeout=30.0,
                description=f"タブ「{self.target_tab_name}」を開く処理",
            )
            if ws is None:
                raise RuntimeError(
                    f"タブ「{self.target_tab_name}」が見つかりませんでした。"
                    "タブ名のスペルミスや、全角/半角の違いがないか確認して"
                    "ください。"
                )
            self.target_ws = ws
            self._log(f"対象タブ: 「{self.target_tab_name}」", "OK")
        else:
            # ★ v45: `ss.sheet1` はプロパティだが、内部でシート一覧を
            #   取得するAPI呼び出しを行うため、他のgspread呼び出しと
            #   同様にネットワーク不調で無期限にブロックしうる。
            #   `_run_with_timeout()` で保護する。
            ws = self._run_with_timeout(
                lambda: ss.sheet1,
                timeout=30.0,
                description="先頭タブを開く処理（sheet1）",
            )
            if ws is None:
                raise RuntimeError(
                    "先頭タブを開けませんでした"
                    "（タイムアウト、またはネットワークエラーの可能性があります）。"
                )
            self.target_ws = ws
            self._log(
                f"対象タブ: 先頭タブ「{self.target_ws.title}」"
                "（タブ名未指定のためデフォルト）",
                "OK",
            )
        return self.target_ws

    # ─────────────────────────────────────────────────────────────
    #  ★ 日次自動実行用: run() の前に呼び出す想定。
    #  A列（ステータス）を全行「対応必要」に上書きし、S列（最終ログイン
    #  日時）・T列（送信人数）を全行クリアしてから、通常どおり run() に
    #  進めるようにする。
    #
    #  毎日決まった時刻に「その日の分をゼロから全部やり直す」運用（＝
    #  前日以前のステータスに関係なく、シートにある全行を今日また対応
    #  必要として扱いたい）を想定して追加した。
    #
    #  注意:
    #    - 既存の run() 内の処理フロー・列定義・ステータス種別は一切
    #      変更していない。run() から見れば、事前にA列が全部「対応必要」
    #      でS/Tが空になっているだけの状態からいつもどおり動くだけ。
    #    - ヘッダー行（1行目）は対象外。2行目以降、実際にデータが入って
    #      いる最終行までを対象にする。
    #    - 1回のAPI呼び出しでまとめて更新する（行ごとに update_cell() を
    #      繰り返すとシートの行数が多い場合にAPIレート制限に引っかかり
    #      やすいため）。
    # ─────────────────────────────────────────────────────────────
    def reset_sheet_for_daily_run(self) -> bool:
        """
        対象シートを「本日分の一括実行」用にリセットする。

        1. ワークシートを開く（未オープンなら _open_target_worksheet()
           を呼ぶ）。
        2. 現在のデータ最終行を取得する。
        3. A2:A{最終行} を全て STATUS_NEED（"対応必要"）に上書きする。
        4. S2:T{最終行} を全て空文字にする（最終ログイン日時・送信人数
           をクリア）。

        戻り値: 成功すれば True。データが無い/失敗した場合は False。
        """
        try:
            if self.target_ws is None:
                self._open_target_worksheet()

            all_values = self._run_with_timeout(
                self.target_ws.get_all_values,
                timeout=30.0,
                description="日次リセットのためのシート読み込み",
            )
            if all_values is None:
                self._log(
                    "シートの読み込みに失敗したため、日次リセットを中止します。",
                    "ERROR",
                )
                return False

            # ★ 修正: len(all_values) は「シート全体の使用範囲」に基づく
            #   ため、H列・I列などにドロップダウンの書式や過去の値が
            #   残っているだけの完全な空行まで「データ行」とみなして
            #   しまい、本来なら空のままでよいA列まで「対応必要」で
            #   埋めてしまう不具合があった。
            #   ここでは「求人番号（F列）が実際に入力されている行」だけを
            #   本物のデータ行とみなし、そこまでを last_row とする。
            last_data_idx = 0  # all_values 内でのインデックス（0-based）
            for idx, row in enumerate(all_values):
                if idx == 0:
                    continue  # ヘッダー行はスキップ
                if _col(row, COL_JOBID).strip():
                    last_data_idx = idx

            if last_data_idx == 0:
                self._log(
                    "リセット対象の行がありません"
                    "（求人番号が入力されているデータ行なし）。",
                    "WARN",
                )
                return False

            last_row = last_data_idx + 1  # 1-indexed のシート行番号に変換
            num_data_rows = last_row - 1  # ヘッダー除く

            # A2:A{last_row} のうち、求人番号（F列）が実際に入っている行
            # だけ「対応必要」にする。それ以外（完全な空行）は空文字の
            # ままにしておく（＝何も書き込まない）。
            status_values = []
            for idx in range(1, last_row):  # all_values の 1..last_row-1
                row = all_values[idx] if idx < len(all_values) else []
                if _col(row, COL_JOBID).strip():
                    status_values.append([STATUS_NEED])
                else:
                    status_values.append([""])

            ok_status = self._run_with_timeout(
                lambda: self.target_ws.update(
                    f"A2:A{last_row}", status_values, value_input_option="RAW"
                ),
                timeout=30.0,
                description="A列を「対応必要」に一括更新",
            )
            if ok_status is None:
                self._log("A列の一括更新に失敗しました。", "ERROR")
                return False

            # S2:T{last_row} を空文字でクリア。
            clear_values = [["", ""] for _ in range(num_data_rows)]
            ok_clear = self._run_with_timeout(
                lambda: self.target_ws.update(
                    f"S2:T{last_row}", clear_values, value_input_option="RAW"
                ),
                timeout=30.0,
                description="S列・T列を一括クリア",
            )
            if ok_clear is None:
                self._log("S列・T列のクリアに失敗しました。", "ERROR")
                return False

            self._log(
                f"日次リセット完了: {num_data_rows} 行を「対応必要」に更新し、"
                "S列・T列をクリアしました。",
                "OK",
            )
            return True

        except Exception as e:
            self._log(f"日次リセット処理でエラーが発生しました: {e}", "ERROR")
            return False

    def _write_cell_with_retry(
        self,
        row_idx: int,
        col_idx_0based: int,
        value: str,
        max_attempts: int = 5,
        base_delay: float = 1.5,
    ) -> bool:
        """
        ★ v28で追加。
        Google Sheets へのセル書き込みをリトライ付きで実行する。

        gspread の `update_cell()` は API レート制限やネットワーク不調で
        まれに失敗することがある。従来はこの例外を握りつぶして ERROR ログを
        出すだけで、それ以降の処理には一切影響させていなかった
        （`_update_status` / `_note_login_time` / `_note_sent_count` 共通）。

        しかしこれには重大なリスクがあった。例えば
        「50人にアプローチ送信 → ステータスを『対応済み』に更新」という
        流れで後半の `update_cell()` が失敗すると、AirWork 側には実際に
        アプローチが送信済みであるにもかかわらず、シート上は
        「対応必要」のまま残ってしまう。次回の bot 実行時、この行は
        再度「対応必要」として処理対象になり、既にアプローチ済みの
        同じ候補者に対してもう一度アプローチを送信してしまう
        （＝重複送信）リスクがあった。

        本メソッドは指数バックオフ付きで最大 `max_attempts` 回まで
        書き込みをリトライすることで、一時的なAPIエラー・ネットワーク
        不調による書き込み失敗の確率を大きく下げる。それでも失敗した
        場合は False を返し、呼び出し側（特に実際の送信が完了した後の
        ステータス更新）で「処理は完了しているがシートに反映できて
        いない」ことを明確に警告できるようにする
        （重複送信リスクを完全には除去できないが、少なくとも
        人手による確認を強く促せるようにする）。

        戻り値: 書き込みに成功すれば True、max_attempts 回失敗すれば False。

        ★ v45で追加。
        `self.target_ws.update_cell()` 自体も、`get_all_values()` や
        `open_by_key()` と全く同じ理由（gspreadの呼び出しに明示的な
        タイムアウトが設定されていない）でネットワーク不調時に無期限に
        ブロックしうる。このメソッドはステータス更新・ログイン時刻記録・
        送信人数記録など1回のrun()の中で非常に高頻度に呼ばれるため、
        `_run_with_timeout()` で1回の試行あたり15秒のタイムアウトガードを
        掛けるようにした。タイムアウトした場合も、通常の例外と同様に
        リトライループの対象として扱う。
        """
        _TIMEOUT_SENTINEL = object()
        last_err_msg = "不明なエラー"
        for attempt in range(1, max_attempts + 1):
            result = self._run_with_timeout(
                lambda: self.target_ws.update_cell(
                    row_idx, col_idx_0based + 1, value
                ),
                timeout=15.0,
                description=f"セル書き込み（行{row_idx}）",
                default=_TIMEOUT_SENTINEL,
            )
            if result is not _TIMEOUT_SENTINEL:
                return True

            last_err_msg = (
                "15秒以内に応答がありませんでした、または書き込み中に"
                "エラーが発生しました（詳細は直前のWARNログを参照）"
            )
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                self._log(
                    f"シート書き込みに失敗しました（{attempt}/{max_attempts}回目、"
                    f"{delay:.1f}秒後に再試行します）: {last_err_msg}",
                    "WARN",
                )
                time.sleep(delay)
        self._log(
            f"シート書き込みが{max_attempts}回とも失敗しました"
            f"（行{row_idx}）: {last_err_msg}",
            "ERROR",
        )
        return False

    def _update_status(self, row_idx: int, status: str) -> bool:
        ok = self._write_cell_with_retry(row_idx, COL_STATUS, status)
        if not ok:
            self._log(
                f"行{row_idx}: ステータス『{status}』への更新が"
                "リトライしても失敗しました。シート上のステータスが"
                "実際の処理結果と食い違っている可能性があるため、"
                "手動で確認してください。",
                "ERROR",
            )
        return ok

    def _update_status_with_reason(
        self, row_idx: int, status: str, reason: Optional[str] = None
    ) -> bool:
        """
        ★ v29で追加。
        ステータスをシートに書き込む。`reason` が指定された場合は
        「ステータス（理由）」の形式でセルに書き込み、ユーザーがシートを
        見ただけでどの工程・どんな理由で処理が止まったのかを判別できる
        ようにする。

        主に STATUS_NEED_CONFIRM（確認必要）を書き込む複数の分岐
        （掲載状況確認／検索条件の反映チェック／無条件検索フォール
        バック／一括送信の人数不足）から呼び出す想定。
        """
        value = status if not reason else f"{status}（{reason}）"
        # セルが極端に長くなりすぎないよう安全のため上限を設ける
        if len(value) > 300:
            value = value[:297] + "..."
        ok = self._write_cell_with_retry(row_idx, COL_STATUS, value)
        if not ok:
            self._log(
                f"行{row_idx}: ステータス『{value}』への更新が"
                "リトライしても失敗しました。シート上のステータスが"
                "実際の処理結果と食い違っている可能性があるため、"
                "手動で確認してください。",
                "ERROR",
            )
        return ok

    def _note_login_time(self, row_idx: int) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self._write_cell_with_retry(row_idx, COL_LOGIN_TIME, now)

    def _note_sent_count(self, row_idx: int, count: int) -> bool:
        ok = self._write_cell_with_retry(row_idx, COL_SENT_COUNT, str(count))
        if not ok:
            self._log(
                f"行{row_idx}: 送信人数『{count}人』のシートへの記録が"
                "リトライしても失敗しました。実際には送信済みの可能性が"
                "あるため、手動で確認してください。",
                "ERROR",
            )
        return ok

    # ─────────────────────────────────────────────────────────────
    #  ★ v35: 1社（AirID）あたりの当日累計送信人数の判定
    # ─────────────────────────────────────────────────────────────
    def _get_company_sent_total_today(self, air_id: str) -> int:
        """
        AirWorkのUI上には1社あたりの当日累計送信人数が集計表示されない
        ため、シート自体の記録から bot が自前で計算する。

        判定方法:
          対象シートの全行のうち、
            - D列（AirID）が引数 air_id と一致する
            - S列（最終ログイン日時。`_note_login_time` が
              "YYYY-MM-DD HH:MM:SS" 形式で書き込む）の日付部分が
              「今日」と一致する
          行のT列（実際に送信したアプローチ人数）を合計する。

        同じ会社が複数の求人（複数行）を持つ場合、1日の送信上限
        （`DAILY_APPROACH_LIMIT_PER_COMPANY`）は会社（AirID）単位で
        共有されるため、行単位ではなくAirID単位で当日分を合算する
        必要がある。

        シート取得に失敗した場合は安全側（＝上限に達していないと
        みなして「条件に合う候補者がいない」と判定してしまわないよう）
        に倒すため、0ではなく便宜上 DAILY_APPROACH_LIMIT_PER_COMPANY を
        返す（＝判定不能時は「上限到達」寄りに倒し、より無難な
        STATUS_NO_CANDIDATES 側に倒れるようにする）。
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        all_values = self._run_with_timeout(
            self.target_ws.get_all_values,
            timeout=30.0,
            description="当日累計送信人数の計算のためのシート取得",
        )
        if all_values is None:
            self._log(
                "当日の累計送信人数の計算に失敗しました"
                "（シート取得エラー/タイムアウトのため安全側の判定に"
                "フォールバックします）。",
                "WARN",
            )
            return DAILY_APPROACH_LIMIT_PER_COMPANY

        total = 0
        for row in all_values[1:]:
            if _col(row, COL_AIRID) != air_id:
                continue
            login_time_str = _col(row, COL_LOGIN_TIME)
            if not login_time_str.startswith(today_str):
                continue
            sent_str = _col(row, COL_SENT_COUNT)
            if not sent_str:
                continue
            try:
                total += int(re.sub(r"\D", "", sent_str))
            except ValueError:
                continue
        return total

    def _decide_no_candidates_status(self, row_idx: int, air_id: str) -> Tuple[str, str]:
        """
        ★ v35で追加、v36で戻り値を (status, reason) のタプルに変更した。
        候補者一覧の空表示メッセージ（「条件に合致する候補者がいないか、
        手動アプローチの上限に達したため、候補者を表示できませんでした」）
        を検知した際、原因が「本当に条件に合う候補者がいない」のか
        「1日の送信上限（1社500人）に達しただけ」なのかを、シートに
        記録された当日の累計送信人数から判定する。

        ★ v36補足: 従来は上限到達と判定した場合に理由（reason）を
        空文字のまま `_record_result` していたため、Chatworkの詳細
        セクションには何も表示されず、集計の見出しに固定で
        「（上限到達等）」と書いていた。しかし STATUS_NO_CANDIDATES は
        この「上限到達」ケースと、v33で追加した「候補者を探すボタンが
        操作不可のまま掲載中が続くケース」の両方で使われており、
        後者は上限到達とは無関係であるため、見出しに固定文言を
        付けると誤解を招く（実際に指摘を受けた）。
        v36では見出しの固定文言をやめ、上限到達と判定した場合も
        具体的な理由文字列を返すようにした。呼び出し側はこれを
        `_record_result` に渡すことで、Chatworkの詳細セクションに
        「1日の送信上限（500人）に達したと判定しました」等の具体的な
        理由が必ず表示されるようになる。

        戻り値: (status, reason)
          - status: STATUS_NO_MATCHING_CANDIDATES または STATUS_NO_CANDIDATES
          - reason: Chatworkの詳細セクションに表示する具体的な理由文字列
        """
        total_today = self._get_company_sent_total_today(air_id)
        if total_today >= DAILY_APPROACH_LIMIT_PER_COMPANY:
            reason = (
                f"1日の送信上限（{DAILY_APPROACH_LIMIT_PER_COMPANY}人）に"
                f"達したと判定しました（当日累計送信人数: {total_today}人）"
            )
            self._log(f"行{row_idx}: AirID «{air_id}» {reason}", "INFO")
            return STATUS_NO_CANDIDATES, reason
        else:
            self._log(
                f"行{row_idx}: AirID «{air_id}» の当日累計送信人数は"
                f"{total_today}人（上限{DAILY_APPROACH_LIMIT_PER_COMPANY}人未満）"
                "のため、条件に合う候補者がいないと判定します。",
                "INFO",
            )
            return STATUS_NO_MATCHING_CANDIDATES, ""

    # ─────────────────────────────────────────────────────────────
    #  ブラウザ / ログイン（★ v2: bot_core.AirWorkBotBase に委譲）
    # ─────────────────────────────────────────────────────────────
    def _get_or_create_bot(self, air_id: str, password: str) -> AirWorkBotBase:
        """
        bot_core.AirWorkBotBase のインスタンスを取得（なければ生成）する。
        ブラウザ・ログインの実装は bot_core.py 側の一箇所だけで保守する。
        """
        if self._bot is None:
            self._bot = AirWorkBotBase(
                username=air_id,
                password=password,
                sheet_id=self.target_sheet_id,   # このタブでは実質未使用
                tab_name="手動アプローチ",         # このタブでは実質未使用
                image_folder="",                  # このタブでは未使用
                config_loader=self._config_loader,
                log_callback=self.log_callback,
                headless=self.headless,
            )
        else:
            # アカウント（会社）が変わった場合はログイン情報だけ差し替える。
            self._bot.username = air_id
            self._bot.password = password
        return self._bot

    def _click_relogin_link_if_present(self) -> bool:
        """
        アカウント切り替え時に表示されることがある「本人確認」画面
        （前回ログインしていた別アカウントのAirIDが読み取り専用で
        表示され、パスワード欄しか無い状態）から、実際にAirID/パスワード
        の両方を入力できるログインフォームまで進める。

        v10: まず
          <a href="https://ats.rct.airwork.net/logout" ...>
            別のAirIDまたはメールアドレスでログインする
          </a>
        をクリックして明示的にログアウトする。

        v12: 上記リンクをクリックした後、connect.airregi.jp 側の
        ログインURL（nonce/state が新しくなった状態）に戻ってくるが、
        実際のAirID/パスワード入力フォームがすぐには表示されず、
          <a class="styles_loginButton__3BIw7 ..." role="button"
             data-theme="primary">ログイン</a>
        という中間ボタンをさらにクリックする必要がある画面が挟まる
        ケースが確認されたため、そのボタンが見つかればクリックする
        処理を追加した。

        戻り値: いずれか（ログアウトリンク／中間ログインボタン）を
        1つでもクリックできれば True。
        """
        driver = self.driver
        if driver is None:
            return False

        clicked_something = False

        # 1) 「別のAirIDまたはメールアドレスでログインする」リンク
        try:
            relogin_link = driver.find_element(
                By.XPATH,
                "//a[contains(@href,'/logout')]"
                "[contains(., '別のAirID') or contains(., '別の') or contains(., 'ログインする')]",
            )
        except NoSuchElementException:
            relogin_link = None

        if relogin_link is not None:
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", relogin_link
                )
                relogin_link.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", relogin_link)
            except Exception as e:
                self._log(f"「別のAirID...」リンクのクリックに失敗しました: {e}", "WARN")
            else:
                self._log(
                    "「別のAirIDまたはメールアドレスでログインする」をクリックして"
                    "ログアウトしました。",
                    "INFO",
                )
                clicked_something = True
                time.sleep(1.5)

        # 2) ログアウト後の中間画面に表示されることがある「ログイン」ボタン
        #    （AirID/パスワード入力フォームへ進むためのボタン）
        try:
            login_btn = self._wait(8).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//*[self::a or self::button]"
                        "[@role='button']"
                        "[contains(@class,'loginButton') or normalize-space(text())='ログイン']",
                    )
                )
            )
        except TimeoutException:
            login_btn = None

        if login_btn is not None:
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", login_btn
                )
                login_btn.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", login_btn)
            except Exception as e:
                self._log(f"中間画面の「ログイン」ボタンのクリックに失敗しました: {e}", "WARN")
            else:
                self._log(
                    "中間画面の「ログイン」ボタンをクリックして"
                    "AirID/パスワード入力フォームへ進みます。",
                    "INFO",
                )
                clicked_something = True
                time.sleep(1.5)

        return clicked_something

    def _click_header_account_arrow(self):
        """
        ヘッダー右上のアカウントメニューを開く矢印アイコンをクリックする。

        実HTML:
          <li class="cmn-hdr-menu-btn cmn-hdr-account">
            ...
            <div class="cmn-hdr-icon cmn-hdr-arrow-down">...</div>
          </li>
        「cmn-hdr-arrow-down」クラスはサービス切り替えメニュー側にも
        存在するため、cmn-hdr-account 配下のものだけを対象にする。
        """
        driver = self.driver
        arrow = self._wait(10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//li[contains(@class,'cmn-hdr-account')]"
                    "//div[contains(@class,'cmn-hdr-arrow-down')]",
                )
            )
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", arrow)
        try:
            arrow.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", arrow)
        time.sleep(0.5)

    def _click_header_logout_link(self):
        """
        アカウントメニュー内の「ログアウト」リンクをクリックする。

        実HTML:
          <div class="cmn-hdr-account-info">
            ...
            <span class="cmn-hdr-logout-menu">
              <a class="cmn-hdr-inner-btn cmn-hdr-logout-link">ログアウト...</a>
            </span>
          </div>
        """
        driver = self.driver
        link = self._wait(10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//div[contains(@class,'cmn-hdr-account-info')]"
                    "//a[contains(@class,'cmn-hdr-logout-link')]",
                )
            )
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", link)
        try:
            link.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", link)
        time.sleep(0.5)

    def _confirm_logout_dialog(self) -> bool:
        """
        「ログアウトの確認」ダイアログの OK ボタンをクリックする。

        実HTML:
          <div id="alert-dialog">
            <div role="alertdialog" ...>
              <header>...ログアウトの確認...</header>
              <p>ログアウトしてよろしいですか？</p>
              <footer>
                <button type="button" data-theme="normal">キャンセル</button>
                <button type="submit" data-theme="primary">OK</button>
              </footer>
            </div>
          </div>
        """
        driver = self.driver
        try:
            ok_btn = self._wait(10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//div[@id='alert-dialog']//button[@type='submit']"
                        " | //div[@role='alertdialog']//button[@type='submit']"
                        " | //div[@id='alert-dialog']//button[contains(., 'OK')]",
                    )
                )
            )
        except TimeoutException:
            self._log("ログアウト確認ダイアログのOKボタンが見つかりません。", "WARN")
            return False

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ok_btn)
        try:
            ok_btn.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", ok_btn)
        time.sleep(1.0)
        return True

    def _click_intermediate_login_button(self) -> bool:
        """
        ログアウト後に表示される、AirID/パスワード入力フォームへ進むための
        中間の「ログイン」ボタンをクリックする（表示されない場合は何もしない）。

        実HTML:
          <a class="styles_loginButton__3BIw7 styles_module__TrDHa"
             role="button" data-theme="primary">ログイン</a>
        """
        driver = self.driver
        try:
            login_btn = self._wait(8).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//*[self::a or self::button]"
                        "[@role='button']"
                        "[contains(@class,'loginButton') or normalize-space(text())='ログイン']",
                    )
                )
            )
        except TimeoutException:
            return False

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", login_btn)
        try:
            login_btn.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", login_btn)
        time.sleep(1.5)
        return True

    def _logout_via_header_menu(self) -> bool:
        """
        会社（AirID）を切り替える前に、ヘッダーのアカウントメニューから
        明示的にログアウトする。

        v14: 従来は「ログイン失敗後に本人確認画面から回復する」という
        事後対応（_click_relogin_link_if_present）のみだったが、それより
        前段階として、そもそも次の会社に切り替える際は毎回このヘッダー
        メニュー経由の正規のログアウト手順を踏むようにした。

        手順:
          1. ヘッダー右上の矢印アイコンをクリックしてアカウントメニューを開く
          2. メニュー内の「ログアウト」リンクをクリック
          3. 「ログアウトの確認」ダイアログの OK ボタンをクリック
          4. ログアウト後に表示される「ログイン」ボタンをクリックして
             AirID/パスワード入力フォームまで進める

        どこかの手順でエラーが起きた場合は途中で諦めて False を返す
        （呼び出し側は _click_relogin_link_if_present() 等の
        フォールバック処理に進める）。
        """
        if self.driver is None:
            return False
        try:
            self._click_header_account_arrow()
            self._click_header_logout_link()
            if not self._confirm_logout_dialog():
                return False
            self._click_intermediate_login_button()
            self._log("ヘッダーメニューからログアウトしました。", "OK")
            return True
        except (TimeoutException, NoSuchElementException) as e:
            self._log(
                f"ヘッダーメニューからのログアウトに失敗しました（{e}）。"
                "別の方法での回復を試みます。",
                "WARN",
            )
            return False

    def _login(self, air_id: str, password: str):
        """
        bot_core.AirWorkBotBase._launch_browser() / _login() に委譲する。
        セレクタ・ログインURLの実装は bot_core.py 側だけで保守すればよい。

        v9: 複数のAirIDを1つのブラウザセッションで使い回して切り替える際、
        直前のアカウントでの操作中にChromeセッションがクラッシュ／無効化
        （invalid session id 等、メッセージが空の WebDriverException）
        しているケースが確認されたため、ログイン試行を例外から保護する。

        v12: 実際には、このクラッシュ（WebDriverException）は必ずしも
        セッション自体の破損が原因ではなく、アカウント切り替え時に
        表示される「本人確認」画面（前回ログインしていた別アカウントの
        AirIDが読み取り専用で表示され、パスワード欄しか無い状態。
        ブラウザに前回ログイン分のセッションCookieが残っている場合に
        発生する）を bot_core.py 側の _login() が想定しておらず、
        内部で予期しない要素操作をして例外になっているケースが多いと
        分かった。そのため、ログイン失敗が「例外によるクラッシュ」でも
        「bot._login() が False を返す通常の失敗」でも、区別せず同じ
        リカバリー処理（_click_relogin_link_if_present() で
        「別のAirIDまたはメールアドレスでログインする」リンク→中間の
        「ログイン」ボタンの順にクリックして本来のAirID/パスワード入力
        フォームまで進める）を試したうえで、最後にもう一度だけ
        ログインを再試行するように統一した。
        """
        from selenium.common.exceptions import WebDriverException

        bot = self._get_or_create_bot(air_id, password)

        def _launch_new_browser():
            self._log(f"AirID «{air_id}» でログインします...", "INFO")
            bot.driver = bot._launch_browser()
            if bot.driver is None:
                raise RuntimeError("ブラウザの起動に失敗しました。")

        def _attempt_login() -> bool:
            try:
                return bool(bot._login(bot.driver))
            except WebDriverException as e:
                self._log(
                    f"ログイン処理中にエラーが発生しました: {e}",
                    "WARN",
                )
                return False

        if bot.driver is None:
            _launch_new_browser()
        else:
            self._log(f"AirID «{air_id}» に切り替えてログインし直します...", "INFO")
            # v14: 会社を切り替える際は、まずヘッダーのアカウントメニューから
            # 明示的にログアウトしてから新しいAirIDでログインを試みる。
            # （失敗しても後続の bot._login() → 回復処理 で従来どおり対応する）
            self._logout_via_header_menu()

        ok = _attempt_login()

        if not ok:
            # まず「本人確認」画面（別のAirIDでログインする リンク／中間の
            # ログインボタン）からの回復を試みる。
            recovered = self._click_relogin_link_if_present()

            if not recovered:
                # リンク／ボタンが見つからなかった場合は、念のため
                # ブラウザ自体を再起動してクリーンな状態から再試行する
                # （セッションが本当にクラッシュしていた場合の保険）。
                self._log(
                    "回復用のリンク／ボタンが見つからなかったため、"
                    "ブラウザを再起動して再試行します...",
                    "WARN",
                )
                try:
                    if bot.driver is not None:
                        # ★ v39: ここも同様に無期限ブロックを防ぐ。
                        self._run_with_timeout(
                            bot.driver.quit,
                            timeout=20.0,
                            description="ブラウザの再起動前の終了処理（driver.quit）",
                        )
                except Exception:
                    pass
                bot.driver = None
                _launch_new_browser()
            else:
                self._log("ログインを再試行します...", "INFO")

            ok = _attempt_login()

        if not ok:
            raise RuntimeError(
                f"AirID «{air_id}» のログインに失敗しました"
                "（bot_core.py の _login() 実装・アカウント情報を確認してください）。"
            )
        self._log("ログイン成功。", "OK")

    def _wait(self, timeout: int = 15) -> WebDriverWait:
        # ★ v27: element_to_be_clickable 等のポーリング中に、要素の
        #   locate 直後（is_displayed() 呼び出し前後など）でReactが
        #   再描画し StaleElementReferenceException になるケースが
        #   実運用ログ（行171）で確認された。WebDriverWait は既定では
        #   NoSuchElementException しか無視しないため、この例外が発生
        #   すると即座にリトライせず呼び出し元まで伝播してしまい、
        #   _click_condition_search_button() などのボタンクリック待ちが
        #   丸ごと失敗して行の処理全体がエラーになっていた。
        #   ignored_exceptions に StaleElementReferenceException を追加し、
        #   発生してもtimeoutまで要素を取得し直しながらリトライするように
        #   した（EC.element_to_be_clickable 等は毎回要素を再locateするため、
        #   stale状態のまま使い続けることはない）。
        return WebDriverWait(
            self.driver,
            timeout,
            ignored_exceptions=(StaleElementReferenceException,),
        )

    # ─────────────────────────────────────────────────────────────
    #  求人番号検索（候補者ページ）
    # ─────────────────────────────────────────────────────────────
    def _search_job_id_on_candidates_page(self, job_id: str) -> bool:
        """
        候補者ページの求人一覧からjob_idを探す。見つかれば True。

        ★ v10 変更点（高速化）
        ---------------------------------------------------------------
        このページには job_offers ページのような検索/絞り込み欄が無く、
        ページ送りしながら <td> の完全一致テキストで探すしかない。
        そのため以下2点で高速化した。

          1) URL に `pageSize=100` を付与し、1ページあたりの表示件数を
             増やして総ページ数自体を減らす。
             このクエリパラメータに対応していない場合は単に無視される
             だけなので、対応していなくても従来通り動作する
             （デグレのリスクは無い）。

          2) 従来は毎ページ固定で time.sleep(1.0) 待ってから判定して
             いたが、これだと「実際は0.3秒で描画が終わるページ」でも
             律儀に1秒待ってしまい、ページ数が多いと合計の無駄待ち時間が
             大きくなっていた。
             v10 では、ページ送りボタンをクリックする直前の1行目の
             <tr> 要素を記憶しておき、クリック後はその要素が
             stale（＝テーブルが再描画された）になるのを
             最大1.5秒・0.15秒間隔でポーリングして待つように変更した。
             描画が速いページではその分だけ早く次の判定に進める。
             1行目要素が取得できなかった場合や staleness 判定が
             タイムアウトした場合は、安全のため短いフォールバック
             待機（0.6秒）を行う。

        ★ v29 変更点
        ---------------------------------------------------------------
        求人番号が実際にはAirWork上に存在するにもかかわらず「見つから
        ない」と誤判定される事例が確認された。原因は、判定に使っていた
        XPath `td[normalize-space(text())=job_id]` が `<td>` 直下の
        テキストノードのみを対象としており、`<td><span>1234567</span>
        </td>` のように数値が子要素（<span> 等）に入っている実装だと
        一致しないことだった。
        v29 では `normalize-space(.)`（`<td>` 配下の全テキストを子要素
        も含めて連結したもの）で判定するように変更した。また、それでも
        見つからなかった場合は原因調査用にデバッグHTML/スクリーン
        ショットを保存するようにした。
        """
        driver = self.driver
        sep = "&" if "?" in CANDIDATES_URL else "?"
        # pageSize は対応していれば総ページ数を減らせるが、未対応でも
        # 単に無視されるだけで安全（job_offers ページでは同様のパラメータが
        # 実際に使われている実績があるため試す価値がある）。
        driver.get(f"{CANDIDATES_URL}{sep}pageSize=100")
        self._wait(20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#__next"))
        )
        time.sleep(0.8)  # 初回描画の猶予（従来の1.0秒より短縮）

        def _job_id_cells():
            # ★ v29: text() → normalize-space(.) に変更。
            #   <td> の子要素（<span>等）にテキストが入っているケースでも
            #   一致するようにするため。
            return driver.find_elements(
                By.XPATH, f"//td[normalize-space(.)={_xpath_literal(job_id)}]"
            )

        max_pages = 60  # 無限ループ防止
        for _ in range(max_pages):
            if self._stopped():
                return False

            if _job_id_cells():
                return True

            # ページ送り前に1行目の要素を記憶（stale判定用）
            try:
                first_row = driver.find_element(By.XPATH, "(//table//tbody//tr)[1]")
            except NoSuchElementException:
                first_row = None

            # 次ページボタンを探してクリック（無効なら終了）
            try:
                next_li = driver.find_element(
                    By.XPATH,
                    "//li[contains(@class,'paginateItem')][.//a[contains(@class,'next')]]",
                )
                if next_li.get_attribute("data-disabled") == "true":
                    break
                next_btn = next_li.find_element(By.XPATH, ".//a[contains(@class,'next')]")
                driver.execute_script("arguments[0].click();", next_btn)
            except NoSuchElementException:
                break

            if first_row is not None:
                try:
                    WebDriverWait(driver, 1.5, poll_frequency=0.15).until(
                        EC.staleness_of(first_row)
                    )
                    continue
                except TimeoutException:
                    pass
            # staleness判定できなかった場合の保険（従来の1.0秒より短縮）
            time.sleep(0.6)

        # ★ v29: 見つからなかった場合、原因調査用にその時点のページ
        #   HTML/スクリーンショットを保存しておく（次に同種の誤判定が
        #   起きた際、実際のtdの構造をすぐ確認できるようにするため）。
        self._dump_debug_snapshot(f"job_id_not_found_{job_id}")
        return False

    def _find_job_row(self, job_id: str):
        """job_id を含む <tr> を返す（見つからなければ None）。"""
        try:
            # ★ v29: text() → normalize-space(.) に変更（理由は
            #   _search_job_id_on_candidates_page の docstring を参照）。
            td = self.driver.find_element(
                By.XPATH, f"//td[normalize-space(.)={_xpath_literal(job_id)}]"
            )
            return td.find_element(By.XPATH, "./ancestor::tr[1]")
        except NoSuchElementException:
            return None

    def _try_click_find_candidates(self, job_id: str):
        """
        「候補者を探す」リンクをクリック試行する。
        戻り値: ("clicked", None) / ("inactive", job_type_text)
        """
        link = self.driver.find_element(
            By.XPATH,
            "//a[@data-la='candidates_search_link_click' and "
            f"@data-la-job-id={_xpath_literal(job_id)}]",
        )
        cls = link.get_attribute("class") or ""
        if "inactive" in cls:
            # 同じ行内の雇用形態テキストを取得
            row = self._find_job_row(job_id)
            job_type_text = ""
            if row is not None:
                try:
                    job_type_text = row.find_element(
                        By.XPATH, ".//div[contains(@class,'jobTypeLocation')]//span"
                    ).text.strip()
                except NoSuchElementException:
                    pass
            return "inactive", job_type_text

        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", link)
        try:
            link.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", link)
        return "clicked", None

    def _check_job_offer_publish_status(self, job_id: str) -> Optional[str]:
        """
        job_offers ページで求人番号検索し、掲載状況テキスト（例:
        「掲載中」「未掲載」等）を返す。

        ★ v29 変更点:
        従来は掲載状況を読み取れなかった場合（タイムアウト）にも
        STATUS_NEED_CONFIRM という文字列を直接返しており、「掲載中
        だった場合」と「読み取り自体に失敗した場合」の2つの異なる
        原因が呼び出し側から区別できなかった。
        v29 では読み取れなかった場合は None を返すように変更し、
        呼び出し側（_process_row）でどちらのケースかをログ・
        ステータス理由に明示できるようにした。
        """
        driver = self.driver
        driver.get(JOB_OFFERS_URL)
        search_input = self._wait(20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[aria-label='InputSearch']"))
        )
        search_input.clear()
        search_input.send_keys(job_id)

        search_btn = driver.find_element(By.XPATH, "//button[@data-la='joboffers_search_btn_click']")
        search_btn.click()
        time.sleep(1.5)

        try:
            status_span = self._wait(15).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class,'publishStatusWrapper')]//span")
                )
            )
            return status_span.text.strip()
        except TimeoutException:
            return None

    # ─────────────────────────────────────────────────────────────
    #  検索条件入力（条件で候補者を探す）
    # ─────────────────────────────────────────────────────────────
    def _click_condition_search_button(self):
        """
        「条件で候補者を探す」ボタンをクリックする。

        v8: 実際のデバッグ用HTML/スクリーンショットを確認したところ、
        ボタン自体は
          <button class="styles_module__r0gvB" data-theme="normal">
            条件で候補者を探す
          </button>
        という単純な構造で、ページ内に同名ボタンは1つだけ、かつ
        role="dialog" 等のモーダルも一切開いていない状態だった。
        Selenium 側では element_to_be_clickable も通り、
        ElementClickIntercepted も発生していなかったため、
        「要素は見えているがReact側のイベントハンドラがまだ紐付いて
        いない」という Next.js のハイドレーション未完了レースコンディション
        が最も疑わしい。

        対策として:
          1) クリック前に document.readyState が 'complete' になるまで待つ。
          2) ハイドレーション猶予として明示的に少し長めに待つ。
          3) ActionChains で実際のマウス操作（move + click）を行う
             （JS実行や単純な .click() よりも本物のユーザー操作に近い）。
          4) クリック前後の URL を記録し、モーダルではなく別ページへの
             遷移だった場合に気付けるようにする。
          5) クリック直後、ボタンの中心座標に実際に乗っている要素を
             document.elementFromPoint() で確認し、透明なオーバーレイ等に
             よってクリックが横取りされていないかログに残す。

        ★ v27: `self._wait()` に ignored_exceptions=(StaleElementReference
        Exception,) を追加したため、ここで使っている
        `EC.element_to_be_clickable` の待機中にstaleが発生しても、この
        メソッド自体は変更せずに自動的にリトライされるようになった。
        """
        from selenium.webdriver.common.action_chains import ActionChains

        # 1) ページの読み込み完了を待つ
        try:
            self._wait(15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            pass

        # 2) ハイドレーション猶予（React側のイベントハンドラ付与待ち）
        time.sleep(1.5)

        btn = self._wait(15).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., '条件で候補者を探す')]")
            )
        )
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.3)

        url_before = self.driver.current_url

        # 5) クリック直前、ボタン中心に実際に乗っている要素を確認
        try:
            top_el_info = self.driver.execute_script(
                """
                var r = arguments[0].getBoundingClientRect();
                var el = document.elementFromPoint(r.left + r.width/2, r.top + r.height/2);
                if (!el) return null;
                return {tag: el.tagName, cls: el.className, text: (el.textContent || '').slice(0, 30)};
                """,
                btn,
            )
            if top_el_info and "条件で候補者" not in (top_el_info.get("text") or ""):
                self._log(
                    f"「条件で候補者を探す」ボタンの位置に別要素が重なっている可能性があります: "
                    f"{top_el_info}",
                    "WARN",
                )
        except Exception:
            top_el_info = None

        # 3) 実際のマウス操作に近い形でクリック
        try:
            ActionChains(self.driver).move_to_element(btn).pause(0.2).click(btn).perform()
        except Exception:
            try:
                btn.click()
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", btn)

        time.sleep(1.2)

        url_after = self.driver.current_url
        if url_after != url_before:
            self._log(
                f"「条件で候補者を探す」クリック後にURLが変化しました: "
                f"{url_before} → {url_after}"
                "（モーダルではなく別ページへの遷移である可能性があります）。",
                "WARN",
            )

    def _wait_for_condition_modal(self, timeout: int = 15, dump_on_fail: bool = True) -> bool:
        """
        「条件の設定」モーダルが実際に開くまで待つ。
        v3: モーダルが開く前に各フィールドを操作しようとして
        NoSuchElementException になる不具合を防ぐために追加。
        v7: 「role='dialog' かつ h3 に『条件の設定』」という厳密すぎる条件
        だけだと、実際のモーダル実装（role属性が無い／見出しタグがh3でない等）
        と一致せず、ボタンのクリック自体は成功しているのにモーダルが
        見つからないと誤判定するケースがあったため、以下2点を追加した。
          1) 判定条件を「本文に『条件の設定』というテキストを含む要素が
             新しく出現したか」まで緩め、role/タグ名に依存しないフォール
             バックを用意した。
          2) それでも見つからない場合は、原因調査のために
             page_source 全文とスクリーンショットを
             /mnt/user-data/outputs/debug_condition_modal.* に保存する
             （次回の調査のため。実運用のPCではカレントの
             outputs フォルダが存在しない場合は保存をスキップする）。
        """
        # 1) 従来どおり role='dialog' + h3 の厳密な判定をまず試す
        try:
            self._wait(timeout).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//div[@role='dialog'][.//h3[contains(text(),'条件の設定')]]",
                    )
                )
            )
            return True
        except TimeoutException:
            pass

        # 2) 緩めたフォールバック: role/タグ名を問わず「条件の設定」という
        #    テキストを含む要素が出ていないか確認する
        try:
            self._wait(5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(text(),'条件の設定')]")
                )
            )
            self._log(
                "「条件の設定」らしき要素は見つかりましたが、想定していた"
                "role='dialog' 構造とは異なるようです。モーダルのHTML構造を"
                "確認し、セレクタの見直しが必要です。",
                "WARN",
            )
            return True
        except TimeoutException:
            pass

        self._log(
            "「条件の設定」モーダルが開きませんでした"
            "（条件で候補者を探す ボタンのクリックに失敗している、"
            "またはボタンが別の要素に隠れてクリックできていない可能性があります）。",
            "WARN",
        )
        if dump_on_fail:
            self._dump_debug_snapshot("condition_modal")
        return False

    def _dump_debug_snapshot(self, tag: str):
        """
        原因調査用に、その時点のページHTMLとスクリーンショットを保存する。
        失敗しても処理全体には影響させない（ベストエフォート）。
        """
        try:
            out_dir = "/mnt/user-data/outputs"
            if not os.path.isdir(out_dir):
                out_dir = os.getcwd()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = os.path.join(out_dir, f"debug_{tag}_{ts}.html")
            png_path = os.path.join(out_dir, f"debug_{tag}_{ts}.png")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            self.driver.save_screenshot(png_path)
            self._log(
                f"調査用にページHTML/スクリーンショットを保存しました: "
                f"{html_path} / {png_path}",
                "INFO",
            )
        except Exception as e:
            self._log(f"デバッグ用スナップショットの保存に失敗しました: {e}", "WARN")

    def _select_option_by_text(self, select_el, text: str):
        try:
            Select(select_el).select_by_visible_text(text)
        except Exception:
            # 完全一致で見つからない場合は部分一致で試す
            for opt in Select(select_el).options:
                if text in opt.text:
                    Select(select_el).select_by_visible_text(opt.text)
                    return

    def _fill_autocomplete(self, placeholder: str, value: str):
        """
        オートコンプリート入力欄（スキル/経験/保有資格など）に値を入力する。

        v11: 「経験を検索する」欄などがモーダル下部にあり、画面下部に
        固定表示されるフッター（styles_footerLeft__xHvfl 等、「検索する」
        ボタンを含む領域）に隠れて box.click() が
        ElementClickInterceptedException になるケースが確認されたため、
        クリック前に要素を画面中央付近までスクロールし、それでも
        インターセプトされた場合は JavaScript 経由のクリックにフォール
        バックするようにした（他のクリック処理と同様のパターン）。
        """
        try:
            box = self.driver.find_element(
                By.XPATH, f"//input[@placeholder='{placeholder}']"
            )
        except NoSuchElementException:
            self._log(f"入力欄が見つかりません: {placeholder}", "WARN")
            return

        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", box
        )
        time.sleep(0.2)
        try:
            box.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", box)

        box.clear()
        box.send_keys(value)
        time.sleep(1.2)  # サジェスト表示待ち
        try:
            suggestion = self.driver.find_element(
                By.XPATH,
                "//div[contains(@class,'suggestItem')][1]"
                " | //button[contains(@class,'buttonList')][1]",
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", suggestion
            )
            try:
                suggestion.click()
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", suggestion)
        except NoSuchElementException:
            # サジェストが出ない場合は Enter で確定を試みる
            box.send_keys(Keys.RETURN)

    def _click_checkbox_by_label(self, label_text: str) -> bool:
        """
        表示テキストが完全一致する <label> をクリックする（汎用フォールバック用）。
        主に希望勤務地（都道府県）のように、チェックボックスの name 属性から
        直接コードを特定できないフィールドに使用する。
        戻り値: クリックできたら True。
        """
        try:
            label = self.driver.find_element(
                By.XPATH,
                f"//label[.//span[normalize-space(text())={_xpath_literal(label_text)}]]",
            )
            self.driver.execute_script("arguments[0].click();", label)
            return True
        except NoSuchElementException:
            self._log(f"チェックボックスが見つかりません: {label_text}", "WARN")
            return False

    def _click_checkbox_by_name(self, name: str) -> bool:
        """
        <input type="checkbox" name="コード"> を name 属性で直接特定してクリックする。
        v3: 最終学歴のチェックボックスは表示テキストが input に紐付いておらず
        name 属性が学歴コードそのものになっているため、こちらを使う。
        """
        try:
            cb = self.driver.find_element(
                By.XPATH, f"//input[@type='checkbox' and @name='{name}']"
            )
            self.driver.execute_script("arguments[0].click();", cb)
            return True
        except NoSuchElementException:
            self._log(f"チェックボックス(name={name})が見つかりません。", "WARN")
            return False

    # ─────────────────────────────────────────────────────────────
    #  「検索する」ボタンのクリック（v8: _apply_conditions から切り出し、
    #  条件あり検索・無条件検索の両方から共通で使えるようにした）
    # ─────────────────────────────────────────────────────────────
    def _click_search_button_in_modal(self) -> bool:
        """
        「条件の設定」モーダル内の「検索する」ボタンをクリックする。

        v6: 「検索する」ボタンは <button data-theme="primary">検索する</button>
            という実装であり、必ずしも <footer> 配下ではなかったため、
            data-theme='primary' を優先しつつ旧セレクタもフォールバックに
            残した XPath に変更。また find_element ではなく
            element_to_be_clickable で明示的に待つことで、ボタンが
            見つからずに click() が失敗する（＝実は検索されていない）
            ケースを防ぐ。
        v13: element_to_be_clickable が通っても、ボタンがモーダル内で
            画面外（スクロール未到達位置）にあると click() が失敗する
            ことがあったため、scrollIntoView を追加し、
            ElementClickInterceptedException が出た場合は JavaScript
            経由のクリックにフォールバックするようにした。
        v8: `_apply_conditions` 内にあった実装をメソッドとして切り出し、
            条件なしで検索するだけの `_search_with_no_conditions` からも
            再利用できるようにした（1回失敗した場合は2秒待って1回だけ
            リトライする点も含めて挙動は従来どおり）。
        """

        def _find_and_click() -> bool:
            try:
                btn = self._wait(10).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//button[@data-theme='primary'][contains(., '検索する')]"
                            " | //footer//button[contains(., '検索する')]",
                        )
                    )
                )
            except TimeoutException:
                return False

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", btn
            )
            time.sleep(0.2)
            try:
                btn.click()
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(1.5)
            return True

        if _find_and_click():
            return True

        self._log(
            "検索するボタンが見つからなかったため、少し待ってもう一度試します...",
            "INFO",
        )
        time.sleep(2.0)
        if _find_and_click():
            return True

        self._log("検索するボタンが見つかりません。", "WARN")
        return False

    def _apply_conditions(self, conditions: Dict[str, str]) -> bool:
        """
        「条件で候補者を探す」モーダルに条件を入力して検索を実行する。

        v6: 戻り値を bool に変更。検索実行後にフィルターバーへ実際に
        反映された条件を読み取り、シートに入力した条件と照合できた場合は
        True、検索ボタンが見つからなかった／条件が反映されていない疑いが
        ある場合は False を返す。呼び出し側（_process_row）はこの戻り値を
        見て、条件が正しく反映されていないと判断した場合はチェックボックス
        の選択・一括アプローチ送信に進まないようにする。

        ★ v29: False を返す各分岐で、原因を `self._last_condition_issue`
        に格納するようにした。呼び出し側はこれを読み取り、「確認必要」の
        理由としてステータスセルに併記する。
        """
        self._last_condition_issue = ""

        self._click_condition_search_button()

        if not self._wait_for_condition_modal(timeout=8, dump_on_fail=False):
            self._log(
                "1回目のクリックでモーダルが開かなかったため、もう一度試します...",
                "INFO",
            )
            self._click_condition_search_button()
            if not self._wait_for_condition_modal():
                self._last_condition_issue = (
                    "「条件の設定」モーダルが開きませんでした"
                )
                return False

        # 希望勤務地
        # v4: 実際のUIを確認したところ、以下の「モーダルの中にもう一つモーダルが
        #     開く」という2段階構造になっていることが判明したため、それに
        #     合わせて実装した。
        #   1) ラジオ hasUsingDesiredLocation=true（"設定する"）をクリックすると、
        #      #DesiredLocation 内に「設定する」という別ボタン
        #      （styles_buttonSetting__dbLof）が表示される。
        #   2) そのボタンをクリックすると、新しいモーダル
        #      role="dialog" aria-label="希望勤務地の設定" が開く。
        #   3) そのモーダルの中で、都道府県ごとに
        #      <input type="checkbox" name="青森県" value="02"> のように
        #      name 属性が都道府県名そのものになっているので、name で直接
        #      特定してチェックする（最大10個まで）。
        #   4) モーダル右下の「保存する」(type="submit") ボタンを押して確定する。
        if conditions.get("希望勤務地"):
            try:
                radio = self.driver.find_element(
                    By.XPATH,
                    "//input[@name='hasUsingDesiredLocation' and @value='true']",
                )
                self.driver.execute_script("arguments[0].click();", radio)
                time.sleep(0.5)

                # ラジオを「設定する」にすると出てくる、都道府県選択モーダルを
                # 開くためのボタン（"設定する"というテキスト、type="button"）。
                setting_btn = self._wait(10).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//div[@id='DesiredLocation']"
                            "//button[contains(., '設定する')]",
                        )
                    )
                )
                setting_btn.click()

                # 「希望勤務地の設定」モーダルが開くまで待つ
                self._wait(10).until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//div[@role='dialog' and @aria-label='希望勤務地の設定']",
                        )
                    )
                )
                time.sleep(0.3)

                prefs = [
                    p.strip()
                    for p in re.split(r"[、,\s]+", conditions["希望勤務地"])
                    if p.strip()
                ]
                if len(prefs) > 10:
                    self._log(
                        f"希望勤務地は最大10個までですが{len(prefs)}個指定されています。"
                        "先頭10個のみ設定します。",
                        "WARN",
                    )
                    prefs = prefs[:10]

                for pref in prefs:
                    try:
                        cb = self.driver.find_element(
                            By.XPATH,
                            "//div[@role='dialog' and @aria-label='希望勤務地の設定']"
                            f"//input[@type='checkbox' and @name={_xpath_literal(pref)}]",
                        )
                        self.driver.execute_script("arguments[0].click();", cb)
                    except NoSuchElementException:
                        self._log(
                            f"希望勤務地『{pref}』のチェックボックスが見つかりません"
                            "（都道府県名の表記ゆれの可能性があります。例：東京都/東京）。",
                            "WARN",
                        )

                # 保存する（モーダル内 footer の submit ボタン）
                try:
                    save_btn = self.driver.find_element(
                        By.XPATH,
                        "//div[@role='dialog' and @aria-label='希望勤務地の設定']"
                        "//button[@type='submit' and contains(., '保存する')]",
                    )
                    save_btn.click()
                    time.sleep(0.8)
                except NoSuchElementException:
                    self._log(
                        "希望勤務地の設定モーダルの「保存する」ボタンが見つかりません。",
                        "WARN",
                    )
            except (NoSuchElementException, TimeoutException):
                self._log(
                    "希望勤務地の設定モーダルを開けませんでした"
                    "（ラジオボタン、または設定するボタンが見つかりません）。",
                    "WARN",
                )

        # 最終学歴
        # v3: 表示テキスト → チェックボックスの name(=学歴コード) に変換して
        #     直接指定する（input には表示テキストが紐付いていないため）。
        if conditions.get("最終学歴"):
            for gakureki in re.split(r"[、,\s]+", conditions["最終学歴"]):
                gakureki = gakureki.strip()
                if not gakureki:
                    continue
                code = EDUCATION_LEVEL_CODE_MAP.get(gakureki)
                if not code:
                    self._log(
                        f"最終学歴『{gakureki}』はコード対応表に存在しません"
                        "（EDUCATION_LEVEL_CODE_MAP を確認してください）。",
                        "WARN",
                    )
                    continue
                self._click_checkbox_by_name(code)

        # 卒業年（年以降 / 年以前）
        if conditions.get("年以降"):
            try:
                el = self.driver.find_element(
                    By.XPATH, "//input[@name='minimumFinalGraduationYear']"
                )
                el.clear()
                el.send_keys(conditions["年以降"])
            except NoSuchElementException:
                self._log("卒業年（年以降）欄が見つかりません。", "WARN")
        if conditions.get("年以前"):
            try:
                el = self.driver.find_element(
                    By.XPATH, "//input[@name='maximumFinalGraduationYear']"
                )
                el.clear()
                el.send_keys(conditions["年以前"])
            except NoSuchElementException:
                self._log("卒業年（年以前）欄が見つかりません。", "WARN")

        # 年齢下限 / 年齢上限
        # v5: <option value="20">20歳</option> のように value 属性が
        #     年齢の数値そのものなので、表示テキストではなく value で
        #     直接指定する（select_by_value）方が確実。
        #     シート側の値は半角数字（例: "20"）を想定。
        if conditions.get("年齢下限"):
            age_value = re.sub(r"\D", "", conditions["年齢下限"])  # 数字以外を除去
            try:
                sel = self.driver.find_element(
                    By.CSS_SELECTOR, "select[name='candidateFilter.minimumAge']"
                )
                if age_value:
                    Select(sel).select_by_value(age_value)
                else:
                    self._log(
                        f"年齢下限『{conditions['年齢下限']}』を数値として解釈できません。",
                        "WARN",
                    )
            except NoSuchElementException:
                self._log("年齢下限のセレクトボックスが見つかりません。", "WARN")
            except Exception as e:
                self._log(f"年齢下限『{age_value}』の選択に失敗しました: {e}", "WARN")
        if conditions.get("年齢上限"):
            age_value = re.sub(r"\D", "", conditions["年齢上限"])
            try:
                sel = self.driver.find_element(
                    By.CSS_SELECTOR, "select[name='candidateFilter.maximumAge']"
                )
                if age_value:
                    Select(sel).select_by_value(age_value)
                else:
                    self._log(
                        f"年齢上限『{conditions['年齢上限']}』を数値として解釈できません。",
                        "WARN",
                    )
            except NoSuchElementException:
                self._log("年齢上限のセレクトボックスが見つかりません。", "WARN")
            except Exception as e:
                self._log(f"年齢上限『{age_value}』の選択に失敗しました: {e}", "WARN")

        # スキル / 経験 / 保有資格（オートコンプリート）
        # v11: 1つのキーワード入力で予期しない例外（クリックインターセプト等）
        # が起きても、残りの条件入力や検索実行が止まらないよう、それぞれの
        # 呼び出しを try/except で保護する。
        if conditions.get("スキル"):
            for kw in re.split(r"[、,\s]+", conditions["スキル"]):
                if kw.strip():
                    try:
                        self._fill_autocomplete("スキルを検索する", kw.strip())
                    except Exception as e:
                        self._log(f"スキル『{kw.strip()}』の入力に失敗しました: {e}", "WARN")
        if conditions.get("経験"):
            for kw in re.split(r"[、,\s]+", conditions["経験"]):
                if kw.strip():
                    try:
                        self._fill_autocomplete("経験を検索する", kw.strip())
                    except Exception as e:
                        self._log(f"経験『{kw.strip()}』の入力に失敗しました: {e}", "WARN")
        if conditions.get("保有資格"):
            for kw in re.split(r"[、,\s]+", conditions["保有資格"]):
                if kw.strip():
                    try:
                        self._fill_autocomplete("保有資格を検索する", kw.strip())
                    except Exception as e:
                        self._log(f"保有資格『{kw.strip()}』の入力に失敗しました: {e}", "WARN")

        # 英会話レベル
        # v3: <option> の value（1〜5）で直接指定する（表示テキストのゆらぎ対策）。
        if conditions.get("英会話レベル") and conditions["英会話レベル"] != "指定なし":
            level_text = conditions["英会話レベル"]
            code = ENGLISH_LEVEL_VALUE_MAP.get(level_text)
            try:
                sel = self.driver.find_element(
                    By.CSS_SELECTOR, "select[name='candidateFilter.englishLevelId']"
                )
                if code:
                    Select(sel).select_by_value(code)
                else:
                    self._log(
                        f"英会話レベル『{level_text}』はコード対応表に存在しません。"
                        "表示テキストでの一致を試みます。",
                        "WARN",
                    )
                    self._select_option_by_text(sel, level_text)
            except NoSuchElementException:
                self._log("英会話レベルのセレクトボックスが見つかりません。", "WARN")

        # 検索実行
        # v8: 検索ボタンのクリック処理は _click_search_button_in_modal()
        #     として切り出し済み（無条件検索フォールバックと共通化）。
        if not self._click_search_button_in_modal():
            self._last_condition_issue = (
                "「検索する」ボタンが見つからず検索を実行できませんでした"
            )
            return False

        # v6: 検索実行後、フィルターバーに表示される「実際に適用された条件」を
        #     読み取り、シートに入力した条件が反映されているか照合する。
        #     反映されていない疑いがある場合は False を返し、呼び出し側で
        #     一括アプローチ送信に進まないようにする（誤送信防止）。
        ok, reason = self._verify_applied_conditions(conditions)
        self._last_condition_issue = reason
        return ok

    # ─────────────────────────────────────────────────────────────
    #  検索条件が未入力の場合のフォールバック（v8で追加）
    # ─────────────────────────────────────────────────────────────
    def _search_with_no_conditions(self) -> bool:
        """
        H〜Q列に検索条件が一切入力されていない行で、「候補者を探す」
        クリック直後のデフォルト画面に候補者が1件も表示されなかった場合の
        フォールバック処理。

        「条件で候補者を探す」モーダルを開き、フィールドには何も入力せず
        「検索する」ボタンだけをクリックすることで、候補者一覧を表示させる。
        （UI側が、一度検索を実行する操作を経ないと一覧を描画しない仕様に
        なっているケースへの対応。）

        戻り値: モーダルを開いて「検索する」ボタンのクリックまで実行
                できれば True（＝一覧が表示されたかどうかは呼び出し側で
                別途 `_count_candidates_on_page()` 等で確認すること）。
        """
        self._log(
            "検索条件が未入力のため、条件を入力せずに「検索する」を実行して"
            "候補者一覧を表示します...",
            "INFO",
        )

        self._click_condition_search_button()

        if not self._wait_for_condition_modal(timeout=8, dump_on_fail=False):
            self._log(
                "1回目のクリックでモーダルが開かなかったため、もう一度試します...",
                "INFO",
            )
            self._click_condition_search_button()
            if not self._wait_for_condition_modal():
                return False

        # フィールドには何も入力せず、そのまま検索するボタンだけを押す。
        return self._click_search_button_in_modal()

    # ─────────────────────────────────────────────────────────────
    #  検索結果の条件反映チェック（v6で追加）
    # ─────────────────────────────────────────────────────────────
    def _get_filter_bar_summary(self) -> Dict[str, object]:
        """
        検索実行後に表示されるフィルターバー（styles_filterBar__...）から、
        実際に適用された条件のテキスト一覧と検索結果件数を取得する。

        例（実HTML）:
          <div class="styles_filterBar__VkMUj">
            <div class="styles_filterLeft__bs8b1">
              <div class="styles_conditionRow__w_ruT">
                <div class="styles_conditionText__sLy0E"><span>年齢：〜29歳</span></div>
                <a class="styles_saveLink__Shf0f ...">この条件を保存する</a>
              </div>
              <span class="styles_filterLabel__6WEzl">検索結果：10000件</span>
            </div>
            ...
          </div>
        """
        texts: List[str] = []
        count_text = ""
        try:
            bar = self._wait(15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[class*='styles_filterBar__']")
                )
            )
        except TimeoutException:
            self._log(
                "検索実行後にフィルターバー（適用条件の表示）が見つかりませんでした。"
                "条件が正しく反映されたか確認できません。",
                "WARN",
            )
            return {"texts": texts, "count_text": count_text}

        for span in bar.find_elements(
            By.CSS_SELECTOR, "div[class*='styles_conditionText__'] span"
        ):
            t = span.text.strip()
            if t:
                texts.append(t)

        try:
            count_el = bar.find_element(
                By.CSS_SELECTOR, "span[class*='styles_filterLabel__']"
            )
            count_text = count_el.text.strip()
        except NoSuchElementException:
            pass

        return {"texts": texts, "count_text": count_text}

    def _verify_applied_conditions(
        self, conditions: Dict[str, str]
    ) -> Tuple[bool, str]:
        """
        検索するボタンを押した後、フィルターバーに表示される「適用中の条件」を
        読み取り、シートに入力した条件が実際に反映されているかをベストエフォート
        で照合する（表示フォーマットはUI依存のため、完全一致ではなく
        「入力値が含まれているか」で判定する）。

        戻り値: (すべての入力済み条件が画面上で確認できれば True で理由は空文字,
                 1つでも確認できない条件があれば False とその理由文字列)

        ★ v29: 戻り値を bool から (bool, reason) のタプルに変更した。
        呼び出し側（_apply_conditions）はこの reason を
        `self._last_condition_issue` に渡し、最終的に「確認必要」の
        ステータスセルへ理由として併記する。
        """
        summary = self._get_filter_bar_summary()
        applied_texts = summary["texts"]

        if applied_texts:
            self._log(f"適用中の条件（画面表示）: {' / '.join(applied_texts)}", "INFO")
        if summary["count_text"]:
            self._log(f"検索結果: {summary['count_text']}", "INFO")

        missing: List[str] = []

        def _found(keyword: str) -> bool:
            return any(keyword in t for t in applied_texts)

        if conditions.get("希望勤務地"):
            for pref in re.split(r"[、,\s]+", conditions["希望勤務地"]):
                pref = pref.strip()
                if pref and not _found(pref):
                    missing.append(f"希望勤務地『{pref}』")

        if conditions.get("最終学歴"):
            for g in re.split(r"[、,\s]+", conditions["最終学歴"]):
                g = g.strip()
                if g and not _found(g):
                    missing.append(f"最終学歴『{g}』")

        if conditions.get("年以降") and not _found(conditions["年以降"]):
            missing.append(f"卒業年（年以降）『{conditions['年以降']}』")
        if conditions.get("年以前") and not _found(conditions["年以前"]):
            missing.append(f"卒業年（年以前）『{conditions['年以前']}』")

        age_lo = re.sub(r"\D", "", conditions.get("年齢下限") or "")
        age_hi = re.sub(r"\D", "", conditions.get("年齢上限") or "")
        if age_lo and not _found(age_lo):
            missing.append(f"年齢下限『{age_lo}』")
        if age_hi and not _found(age_hi):
            missing.append(f"年齢上限『{age_hi}』")

        for key in ("スキル", "経験", "保有資格"):
            if conditions.get(key):
                for kw in re.split(r"[、,\s]+", conditions[key]):
                    kw = kw.strip()
                    if kw and not _found(kw):
                        missing.append(f"{key}『{kw}』")

        if conditions.get("英会話レベル") and conditions["英会話レベル"] != "指定なし":
            if not _found(conditions["英会話レベル"]):
                missing.append(f"英会話レベル『{conditions['英会話レベル']}』")

        if missing:
            reason = "入力条件が画面に反映されていません: " + " / ".join(missing)
            self._log(
                "画面上の適用条件に、入力したはずの条件が反映されていない可能性があります: "
                + " / ".join(missing),
                "WARN",
            )
            return False, reason

        self._log("入力した検索条件はすべて画面上に反映されていることを確認しました。", "OK")
        return True, ""

    # ─────────────────────────────────────────────────────────────
    #  検索結果の空表示チェック（v7で追加）
    # ─────────────────────────────────────────────────────────────
    def _check_no_candidates_message(self, timeout: float = 3.0) -> bool:
        """
        候補者一覧の代わりに以下のような空表示メッセージが出ていないかを
        確認する。

          <p class="styles_noSearchText__y7Hox">
            条件に合致する候補者がいないか、手動アプローチの上限に達したため、
            候補者を表示できませんでした。
          </p>

        v7: 条件検索した場合・条件なしでそのまま候補者一覧に来た場合の
        どちらでも、一括アプローチ送信の直前に呼び出す想定。

        class名（styles_noSearchText__...）はビルドごとにハッシュ部分が
        変わる可能性があるため、`class*=` の部分一致セレクタを優先しつつ、
        見つからない場合はメッセージ本文のテキスト内容でのフォールバック
        判定も行う。

        戻り値: 空表示メッセージが見つかれば True。
        """
        try:
            self._wait(timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "p[class*='styles_noSearchText__']")
                )
            )
            return True
        except TimeoutException:
            pass

        # フォールバック: class名に依存せず、メッセージ本文の一部一致で判定する
        try:
            self.driver.find_element(
                By.XPATH,
                "//p[contains(., '候補者を表示できませんでした')]"
                " | //*[contains(., '候補者を表示できませんでした')]"
                "[self::p or self::div or self::span]",
            )
            return True
        except NoSuchElementException:
            return False

    def _wait_for_candidates_or_empty(self, timeout: float = 15.0) -> bool:
        """
        ★ v19: 検索条件の適用（フィルターバーの表示）が完了した直後でも、
        実際の候補者カード（チェックボックス付き）の描画が数秒遅れる
        ケースが確認された。この描画が終わる前に
        `_count_candidates_on_page()` を呼ぶと 0 件と判定されてしまい、
        実際には候補者がいるにもかかわらず `_send_bulk_approach()` が
        何もせずに終了してしまう（「まとめてアプローチ」ボタンを一度も
        探しに行かないまま 0人 で終わる）という不具合が発生していた。

        このメソッドは、候補者のチェックボックスが1件以上表示される
        か、「候補者を表示できませんでした」という空表示メッセージが
        出るまで、短い間隔でポーリングして待つ。どちらかが確認できた
        時点で即座に return する。timeout まで待っても両方とも確認
        できない場合は、それ以上は待たずに終了する（呼び出し側の
        既存のチェックに委ねる）。

        戻り値: 実際には使わないが、候補者が1件以上見つかった場合は
                True、それ以外（空表示メッセージが出た、またはtimeout）
                は False を返す。
        """
        deadline = time.time() + timeout
        poll_interval = 0.5
        while time.time() < deadline:
            if self._stopped():
                return False
            if self._count_candidates_on_page() > 0:
                return True
            if self._check_no_candidates_message(timeout=0.3):
                return False
            time.sleep(poll_interval)
        return self._count_candidates_on_page() > 0

    # ─────────────────────────────────────────────────────────────
    #  一括アプローチ送信
    # ─────────────────────────────────────────────────────────────
    def _wait_for_bulk_button_enabled(self, timeout: float = 5.0) -> bool:
        """
        「まとめてアプローチ」ボタンの disabled 属性が外れる
        （＝チェックボックスの選択がUIに反映され、送信可能な状態になった）
        のを待つ。

        ★ v23で追加。
        実際のHTMLを確認したところ、候補者を1件も選択していない状態では

          <button disabled="" class="styles_btnUpload__snR_0 ..."
                  data-theme="primary">まとめてアプローチ</button>

        のように disabled 属性付きでボタン自体は常にDOM上に存在して
        いることが判明した。つまり、このボタンが見つからない／
        `element_to_be_clickable` にならない状態には、
          (a) 送信処理中で一時的に隠れている（styles_processingContainer__
              が表示されている）場合
          (b) チェックボックスが1件も選択されておらず disabled のまま
              になっている場合
        の2パターンがあり、これらは原因も対処法も異なる
        （(a) は待てば自然に解消するが、(b) はチェックボックスを
        選択し直さない限り何度待っても解消しない）。

        本メソッドは (b) のケースを検知するために使う。選択操作
        （`_select_all_checkbox()` / `_select_individual_checkboxes()`）
        の直後に呼び出し、ボタンが実際に有効化されたかを確認する。

        ★ v26補足: (a)(b) に加えて「処理中で候補者チェックボックス自体が
        disabled になっている」ケースも存在することが判明した。このケース
        では「まとめてアプローチ」ボタンが disabled どころか処理中表示に
        置き換わってDOM上に存在しないことが多いため、本メソッドは
        TimeoutException（＝有効なボタンが見つからない）を返し、
        呼び出し側の `_select_candidates_for_batch()` が選択リトライに
        入る。v26では、そのリトライへ入る前に `_send_bulk_approach()` 側で
        `_wait_until_not_processing()` を呼んで処理中状態を解消してから
        選択するようにしたため、本メソッドが (b) のケース以外で
        False を返すことは通常なくなっているはずである。
        """
        try:
            self._wait(timeout).until(
                lambda d: len(
                    d.find_elements(
                        By.XPATH,
                        "//button[contains(., 'まとめてアプローチ')][not(@disabled)]",
                    )
                )
                > 0
            )
            return True
        except TimeoutException:
            return False

    def _select_all_checkbox(self):
        """
        「すべて選択」チェックボックスをクリックする。

        ★ v24で追加（v23までの根本原因の修正）。
        v23で追加した `_wait_for_bulk_button_enabled()` による検証の結果、
        ページ送り（`_go_to_next_candidate_page()`）直後に候補者一覧が
        丸ごと再描画された直後、このチェックボックスをクリックしても
        「まとめてアプローチ」ボタンが disabled のまま変化しない事象が
        確認された。

        実HTMLを確認したところ、このチェックボックスは

          <label ...>
            <span ...><input type="checkbox" aria-label="isSelectionAll">
              <span></span></span>
            <span>すべて選択</span>
          </label>

        のように <label> でラップされており、input 自体はカスタム
        スタイリングのため画面上は非表示（クリック不可能な位置・サイズ）
        になっている。従来は input に対して `execute_script` 経由の
        JavaScript クリックを行っていたが、これは
        `_click_condition_search_button()` で対処した Next.js の
        ハイドレーション未完了レースコンディション（要素はDOM上に存在し
        JSクリックも例外なく成功するが、Reactのイベントハンドラがまだ
        バインドされておらず、状態変更が一切反映されない）と同様の
        現象を起こしやすいと考えられる。1バッチ目（ページ最初の
        読み込みから十分な待ち時間が経過した状態）では問題なく機能して
        いたが、ページ送り直後（既存の待機は1.2秒のみ）の2バッチ目以降で
        再現していたことも、この仮説と整合する。

        v24 では、input ではなく実際に画面上でクリック可能な <label> を
        対象に、`_click_condition_search_button()` と同様の対策
        （document.readyState 待ち＋ハイドレーション猶予＋ActionChains
        による本物のマウス操作）を適用する。ラベル要素が見つからない、
        または操作に失敗した場合は、従来どおり input への JavaScript
        クリックにフォールバックする。

        ★ v26補足: このチェックボックス自体が「処理中は disabled になる」
        ことが判明したため（ファイル冒頭の v26 変更点を参照）、本メソッド
        を呼ぶ前に呼び出し側（`_send_bulk_approach()`）で
        `_wait_until_not_processing()` により disabled が解消しているのを
        確認してから呼び出す運用に変更した。本メソッド自体は disabled か
        どうかを見ていないため変更していない。
        """
        from selenium.webdriver.common.action_chains import ActionChains

        try:
            self._wait(10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            pass
        time.sleep(0.8)

        label = None
        try:
            label = self.driver.find_element(
                By.XPATH,
                "//input[@aria-label='isSelectionAll']/ancestor::label[1]",
            )
        except NoSuchElementException:
            label = None

        if label is not None:
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", label
                )
                time.sleep(0.2)
                ActionChains(self.driver).move_to_element(label).pause(
                    0.15
                ).click(label).perform()
                return
            except Exception as e:
                self._log(
                    "「すべて選択」ラベルへの実クリックに失敗しました"
                    f"（{e}）。input への JavaScript クリックにフォールバック"
                    "します。",
                    "WARN",
                )

        cb = self.driver.find_element(
            By.XPATH, "//input[@aria-label='isSelectionAll']"
        )
        self.driver.execute_script("arguments[0].click();", cb)

    def _count_checked_candidate_checkboxes(self) -> int:
        """
        ★ v28で追加。
        実際にチェック状態になっている候補者チェックボックスの数を
        DOM から直接数える。

        `_select_candidates_for_batch()` は従来、"すべて選択" を使う
        バッチでは `take = min(50, available)` のように「1ページ=50件」
        という前提で選択人数を見積もっていた。しかし `_select_all_checkbox()`
        は実際に画面上に表示されている候補者を"全員"選択するため、
        もし何らかの理由でページの表示件数が50件を超える場合（UI仕様の
        変更等）、実際に選択・送信される人数は見積もりより多くなり、
        `total_sent` の記録が実際にAirWork側へ送信した人数より
        少なく計上されてしまう不整合が起こり得た。

        本メソッドはチェックボックスの実際のチェック状態を数えることで、
        見積もり値ではなく「実際に選択されている人数」を確認できるように
        する。
        """
        try:
            return int(
                self.driver.execute_script(
                    "return document.querySelectorAll("
                    "\"input[data-la*='jobseekers_checkbox_click']:checked\""
                    ").length;"
                )
                or 0
            )
        except Exception:
            return 0

    def _select_individual_checkboxes(self, count: int) -> int:
        """
        先頭から count 件だけ個別チェックする。実際に選んだ件数を返す。

        ★ v9: 従来は候補者数（最大50件/ページ）分だけ execute_script() を
        ループで個別に呼んでおり、1件ごとに Selenium ⇔ ブラウザ間の
        IPCラウンドトリップが発生していたため、50件選択するのに数秒
        かかることがあった。
        ここでは対象チェックボックス要素の配列をまとめて1回の
        execute_script() に渡し、ブラウザ側のJavaScriptループで一括
        クリックするように変更した（IPC往復を「N回」から「1回」に削減）。
        個々の要素が stale だった場合でも他の要素の選択を止めないよう、
        JS側の forEach 内で try/catch している
        （従来の StaleElementReferenceException 握りつぶしと同等の挙動）。
        """
        checkboxes = self.driver.find_elements(
            By.XPATH, "//input[contains(@data-la,'jobseekers_checkbox_click')]"
        )
        n = min(count, len(checkboxes))
        targets = checkboxes[:n]
        if targets:
            try:
                self.driver.execute_script(
                    """
                    var els = arguments[0];
                    for (var i = 0; i < els.length; i++) {
                        try { els[i].click(); } catch (e) { /* stale等は無視して継続 */ }
                    }
                    """,
                    targets,
                )
            except StaleElementReferenceException:
                # 配列全体が無効化されていた場合のみのフォールバック。
                # 通常はJS側のtry/catchで個別に吸収されるため稀。
                pass
        return n

    def _click_confirm_send_button(self, timeout: float = 10.0) -> bool:
        """
        ★ v17: 「○人にまとめてアプローチ」ボタンをクリックした後に表示される
        確認ダイアログ／確認画面の中にある、実際に送信を確定させるボタン
        「アプローチを送る」をクリックする。

        実際の動作を確認したところ、一括アプローチの送信は次の2段階に
        なっていることが判明した。

          1. 候補者一覧画面の「○人にまとめてアプローチ」ボタン
             （data-la="jobseekers_checkbox_click" 系のチェックボックスで
             選択した候補者数に応じたラベルのボタン）をクリックする。
             → これは確認ダイアログ／確認画面を開くだけで、まだ実際の
               送信は行われない。

          2. 確認ダイアログ内の
                <button type="button" data-theme="primary">
                  アプローチを送る
                </button>
             をクリックして初めて、実際の送信処理が開始される。
             このクリック後、約1秒で「まとめてアプローチを送信中...」
             という処理中表示に切り替わり、その後
             「更新して状況を確認する」を押して初めて
             「送信完了」の本物の成功通知が表示される。

        v16までの実装は手順1のボタンしかクリックしておらず、手順2の
        「アプローチを送る」ボタンを一度もクリックしていなかったため、
        実際には送信が確定していなかった（＝bot が「送信できた」と
        ログに出していても、AirWork側では何も送信されていなかった）。

        本メソッドは手順2の「アプローチを送る」ボタンを探してクリックする。
        戻り値: クリックできれば True。ボタンが見つからない場合
                （＝環境によっては確認ダイアログが出ない、または
                ボタンの文言が異なる可能性があるため）は False を返し、
                呼び出し側でログに警告を残す。

        ★ v38補足: `self._wait().until(EC.element_to_be_clickable(...))`
        自体はstale発生時に要素を再locateしながらポーリングするため
        （v27）ロケート段階は頑健だが、`until()` が要素を返した直後の
        `btn.click()` 呼び出し自体がstaleになるケースは従来防げていな
        かった。本メソッドは実際の送信を確定させる最重要のクリックで
        あるため、`_click_refresh_status_button()` と同様にクリック時の
        stale発生に対しても要素を取得し直してリトライするようにした。
        """
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                btn = self._wait(timeout).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//button[@type='button']"
                            "[contains(., 'アプローチを送る')]",
                        )
                    )
                )
            except TimeoutException:
                return False

            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", btn
                )
                time.sleep(0.2)
                btn.click()
                return True
            except StaleElementReferenceException:
                if attempt < max_attempts:
                    self._log(
                        "「アプローチを送る」ボタンの取得直後にDOMが再描画され、"
                        f"要素が古くなりました（stale）。取得し直して再試行します"
                        f"（{attempt}回目）...",
                        "WARN",
                    )
                    time.sleep(0.5)
                    continue
                self._log(
                    f"「アプローチを送る」ボタンが{max_attempts}回とも stale で"
                    "クリックできませんでした。",
                    "WARN",
                )
                return False
            except ElementClickInterceptedException:
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                    return True
                except StaleElementReferenceException:
                    if attempt < max_attempts:
                        time.sleep(0.5)
                        continue
                    return False

        return False

    # ─────────────────────────────────────────────────────────────
    #  ★ v16: AirWork側の本物の成功通知（送信完了）を読み取る
    #  （まとめてアプローチは非同期処理のため、処理中→更新→完了の
    #   ポーリングが必要）
    # ─────────────────────────────────────────────────────────────
    def _peek_success_message(self) -> Optional[Dict[str, str]]:
        """
        現在のDOMに、AirWork側の本物の成功通知（送信完了）が既に
        表示されているかを即座に（待たずに）確認する。

        実HTML:
          <div class="styles_success__iNsRZ styles_message__iyXyu" data-type="success">
            <div class="styles_messageItem__rI7WY">
              ...
              <span class="styles_messageSuccessTitle__c_ruF">送信完了</span>
              <span class="styles_messageDate__fd9wX">2026/7/14 11:15 送信</span>
            </div>
          </div>

        戻り値: 見つかった場合はタイトルと送信日時文字列を含む辞書。
                見つからなければ None（待機はしない）。
        """
        try:
            box = self.driver.find_element(
                By.CSS_SELECTOR, "div[class*='styles_success__'][data-type='success']"
            )
        except NoSuchElementException:
            return None

        title = ""
        date_text = ""
        try:
            title = box.find_element(
                By.CSS_SELECTOR, "span[class*='messageSuccessTitle__']"
            ).text.strip()
        except NoSuchElementException:
            pass
        try:
            date_text = box.find_element(
                By.CSS_SELECTOR, "span[class*='messageDate__']"
            ).text.strip()
        except NoSuchElementException:
            pass

        if not title:
            return None
        return {"title": title, "date_text": date_text}

    def _is_processing(self) -> bool:
        """
        「まとめてアプローチを送信中...」という非同期処理中の表示が
        出ているかを確認する。

        実HTML:
          <div class="styles_processingContainer__Zj2zt">
            <div class="styles_loader__NHNIO">...</div>
            <span class="styles_statusText__AF7cx">
              まとめてアプローチを送信中...
            </span>
            <button type="button" class="styles_refreshLink__TONqo ..."
                    data-theme="text_primary">
              更新して状況を確認する
            </button>
          </div>

        ★ v26補足: この表示が出ている間は、候補者一覧の「すべて選択」
        チェックボックス、および個々の候補者チェックボックスも
        disabled 属性が付与され、選択操作自体ができない状態になって
        いることを実HTMLで確認済み（ファイル冒頭の v26 変更点を参照）。
        そのため、次バッチの選択操作を行う前に、本メソッドが False を
        返す（＝処理中表示が消えている）ことを `_wait_until_not_processing()`
        で確認するようにしている。
        """
        try:
            self.driver.find_element(
                By.CSS_SELECTOR, "div[class*='styles_processingContainer__']"
            )
            return True
        except NoSuchElementException:
            return False

    def _click_refresh_status_button(self, max_attempts: int = 3) -> bool:
        """
        処理中表示の中にある「更新して状況を確認する」ボタンをクリックする。

        ★ v38で追加。
        実運用ログで、この直後の `btn.click()` にて
        `StaleElementReferenceException` が発生し、その行の処理全体が
        `except Exception` まで伝播して失敗するケースが確認された
        （行113）。

        原因は、AirWork側が「処理中」→「送信完了」に状態を切り替える
        タイミングと、本メソッドが要素を取得してからクリックするまでの
        わずかな間にReactがDOMを再描画するタイミングが重なり、取得した
        `WebElement` が古くなる（stale になる）ことである。これは
        `_locate_and_click_bulk_button()`（v21で対策済み）と全く同種の
        レースコンディションだが、本メソッドはそちらとは別に独自実装
        されており、対策が漏れていた。

        本メソッドはボタンの探索とクリックを最大 `max_attempts` 回まで
        リトライし、`StaleElementReferenceException` が発生した場合は
        要素を取得し直して再試行する
        （`ElementClickInterceptedException` の場合の JavaScript クリック
        へのフォールバックは従来どおり維持）。
        戻り値: クリックできれば True。ボタン自体が存在しない
                （NoSuchElementException）、またはリトライしても
                stale が解消しなかった場合は False。
        """
        for attempt in range(1, max_attempts + 1):
            try:
                btn = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(@class,'styles_refreshLink__')]"
                    "[contains(., '更新して状況を確認する')]",
                )
            except NoSuchElementException:
                return False

            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", btn
                )
                btn.click()
                return True
            except StaleElementReferenceException:
                if attempt < max_attempts:
                    self._log(
                        "「更新して状況を確認する」ボタンの取得直後にDOMが"
                        f"再描画され、要素が古くなりました（stale）。取得し直して"
                        f"再試行します（{attempt}回目）...",
                        "WARN",
                    )
                    time.sleep(0.5)
                    continue
                self._log(
                    "「更新して状況を確認する」ボタンが"
                    f"{max_attempts}回とも stale で取得できませんでした。",
                    "WARN",
                )
                return False
            except ElementClickInterceptedException:
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                    return True
                except StaleElementReferenceException:
                    if attempt < max_attempts:
                        time.sleep(0.5)
                        continue
                    return False

        return False

    def _wait_until_not_processing(
        self, timeout: float = 60.0, poll_interval: float = 2.0
    ) -> bool:
        """
        ★ v26で追加。

        原因調査用に保存されたデバッグHTML/スクリーンショット
        （debug_selection_not_reflected_*）を確認したところ、
        「まとめてアプローチを送信中...」という処理中表示
        （`_is_processing()` が True）が出ている間は、以下のように
        「すべて選択」チェックボックスも個々の候補者チェックボックスも
        `disabled` 属性が付与され、クリックしても一切選択できない状態に
        なっていることが判明した。

          <input aria-label="isSelectionAll" ... disabled>
          <input data-la="jobseekers_checkbox_click" ... disabled>

        従来 `_click_bulk_approach_button()` 末尾の「まとめてアプローチ」
        ボタン再出現待ちループは最大15秒しか待っておらず、AirWork側の
        処理がそれより長引くケースでは、まだ処理中＝チェックボックスが
        disabled のまま次バッチの選択処理へ進んでしまっていた。この状態で
        `_select_candidates_for_batch()` が選択操作をリトライしても、
        そもそも操作対象が disabled であるため何度リトライしても解決せず、
        「選択してもボタンが有効にならない」という誤った警告とともに
        バッチ送信が打ち切られていた。

        本メソッドは、次バッチの選択操作を始める前に呼び出し、処理中表示
        （`_is_processing()`）が完全に消える（＝チェックボックスが再度
        有効になる）まで、「更新して状況を確認する」ボタンを押しながら
        ポーリングして待つ。`_read_success_message()` と同様のポーリング
        構造を用いている。

        戻り値: timeout以内に処理中表示が消えれば True。
                timeoutまで消えなければ False
                （呼び出し側でそのバッチ送信を打ち切ることを想定）。
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._stopped():
                return False
            if not self._is_processing():
                return True
            self._click_refresh_status_button()
            time.sleep(poll_interval)
        return not self._is_processing()

    def _read_success_message(
        self, timeout: float = 60.0, poll_interval: float = 2.0
    ) -> Optional[Dict[str, str]]:
        """
        ★ v16: 「まとめてアプローチ」の送信はAirWork側で非同期に処理される。
        ボタンを押した直後は

          <div class="styles_processingContainer__...">
            ...まとめてアプローチを送信中...
            <button ...>更新して状況を確認する</button>
          </div>

        という「処理中」表示になり、本物の成功通知（送信完了）はすぐには
        出ない。処理中表示が出ている間は「更新して状況を確認する」ボタンを
        繰り返しクリックして状況を再取得し、本物の成功通知
        （styles_success__...[data-type='success']、
        「送信完了」というタイトル）が表示されるまで待つ必要がある。

        このポーリングを行わずに1回だけDOMを確認すると、まだ処理中の
        タイミングでは「通知が見つからない＝失敗かもしれない」と誤判定
        してしまうため、v16では以下のポーリングループに変更した。

          1. 既に成功通知が出ていれば、それを返して終了。
          2. 処理中表示が出ていれば、「更新して状況を確認する」ボタンを
             クリックして少し待ち、1に戻る。
          3. 処理中表示も成功通知も無い場合は、少し待って再確認する
             （表示が切り替わる過渡的なタイミングの可能性があるため）。
          4. timeout秒経過しても成功通知が確認できなければ None を返す。

        戻り値: 見つかった場合はタイトルと送信日時文字列を含む辞書。
                timeoutまでに確認できなければ None。
        """
        deadline = time.time() + timeout

        while time.time() < deadline:
            if self._stopped():
                return None

            # 1) 既に本物の成功通知が出ているか確認
            result = self._peek_success_message()
            if result is not None:
                return result

            # 2) 処理中表示が出ていれば、更新ボタンを押して再確認を促す
            if self._is_processing():
                self._log(
                    "AirWork側でまとめてアプローチを処理中です。"
                    "「更新して状況を確認する」で状況を再確認します...",
                    "INFO",
                )
                self._click_refresh_status_button()
                time.sleep(poll_interval)
                continue

            # 3) どちらの表示も無い場合、表示切り替え中の可能性があるため
            #    少し待って次のループで再確認する。
            time.sleep(poll_interval)

        return None

    def _locate_and_click_bulk_button(self, total_timeout: float = 45.0) -> bool:
        """
        「まとめてアプローチ」ボタンを取得してクリックする。

        ★ v21で追加。
        `element_to_be_clickable` で要素を取得した直後、Reactが再描画して
        その要素を差し替えてしまい、取得済みの WebElement 参照が古くなる
        （stale になる）レースコンディションが実運用で確認された
        （v20の「まとめてアプローチ」ボタン再出現待ちループの直後など、
        直前まで処理中表示⇔ボタン表示の切り替えが頻発していた場面で
        特に発生しやすい）。

        従来は要素取得〜クリックを1回しか試みておらず、
        `StaleElementReferenceException` を捕捉していなかったため、
        この例外がそのまま `_process_row` の `except Exception` まで
        伝播し、その行の処理全体が失敗していた。

        本メソッドでは、要素の取得とクリックをセットにしてリトライし、
        `StaleElementReferenceException` が発生した場合は少し待って
        要素を取得し直す。`ElementClickInterceptedException` の場合は
        従来どおり JavaScript 経由のクリックにフォールバックする。

        ★ v22で追加（連続バッチ送信時に「まとめてアプローチ」ボタンが
        見つからず即座に諦めてしまう不具合の修正）。
        ---------------------------------------------------------------
        実運用で、1バッチ目の送信完了後、ヘッダー部分が
        「まとめてアプローチを送信中...」（処理中表示）のまま
        `_click_bulk_approach_button()` 末尾の再出現待ちループ
        （最大15秒）内では回復しきらず、次バッチの
        `_locate_and_click_bulk_button()` が呼ばれた時点でもまだ
        処理中表示のままになっているケースが確認された。

        従来の実装は、1回目の `element_to_be_clickable` の待機
        （10秒）で `TimeoutException` になった時点で即座に
        `False` を返して諦めていたため、実際にはあと数秒〜数十秒
        待てば処理中表示が解消してボタンが再表示されるはずの状況でも、
        そのバッチの送信を放棄してしまっていた（G列の目標人数に届かず
        「確認必要」になる原因）。

        v22 では、`TimeoutException` になった場合でも即座には諦めず、
        以下のロジックで `total_timeout` 秒（既定45秒）に達するまで
        ポーリングを続けるようにした。
          1. 処理中表示（`_is_processing()`）が出ていれば、
             「更新して状況を確認する」ボタンをクリックして状況を
             再取得し、少し待ってから再度ボタンの出現を試みる。
          2. 処理中表示も出ていない場合（表示切り替え中の過渡的な
             タイミングの可能性があるため）も、少し待って再試行する。
          3. `total_timeout` 秒経過してもボタンが見つからなければ
             `False` を返す（呼び出し側で「確認必要」に回される）。

        戻り値: クリックできれば True。`total_timeout` 秒待っても
                クリックできなければ False。
        """
        deadline = time.time() + total_timeout
        attempt = 0

        while time.time() < deadline:
            attempt += 1
            remaining = max(1.0, deadline - time.time())
            per_wait = min(10.0, remaining)

            try:
                btn = self._wait(per_wait).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(., 'まとめてアプローチ')]")
                    )
                )
            except TimeoutException:
                if self._stopped():
                    return False
                if self._is_processing():
                    self._log(
                        "「まとめてアプローチ」ボタンがまだ表示されません"
                        "（処理中表示が続いています）。「更新して状況を確認する」で"
                        "再確認します...",
                        "INFO",
                    )
                    self._click_refresh_status_button()
                else:
                    self._log(
                        "「まとめてアプローチ」ボタンがまだ見つかりません。"
                        "表示切り替え中の可能性があるため、少し待って再確認します"
                        f"（経過 {total_timeout - (deadline - time.time()):.0f}秒 /"
                        f" 最大{total_timeout:.0f}秒）...",
                        "INFO",
                    )
                time.sleep(1.5)
                continue

            try:
                btn.click()
                return True
            except StaleElementReferenceException:
                self._log(
                    "「まとめてアプローチ」ボタンの取得直後にDOMが再描画され、"
                    "要素が古くなりました（stale）。取得し直して再試行します"
                    f"（{attempt}回目）...",
                    "WARN",
                )
                time.sleep(0.5)
                continue
            except ElementClickInterceptedException:
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                    return True
                except StaleElementReferenceException:
                    self._log(
                        "「まとめてアプローチ」ボタンがクリック直前に再度staleに"
                        f"なりました。取得し直して再試行します（{attempt}回目）...",
                        "WARN",
                    )
                    time.sleep(0.5)
                    continue

        self._log(
            f"「まとめてアプローチ」ボタンが{total_timeout:.0f}秒待っても"
            "見つかりませんでした。",
            "WARN",
        )
        return False

    def _click_bulk_approach_button(self) -> bool:
        """
        「まとめてアプローチ」ボタンを押し、確認ダイアログの
        「アプローチを送る」ボタンで送信を確定させる。

        ★ v17 変更点（v16からの改良）:
        実際の動作を確認したところ、一括アプローチの送信は次の2段階に
        なっていることが判明した。

          1. 候補者一覧画面の「○人にまとめてアプローチ」ボタンを
             クリックする → 確認ダイアログが開くだけで、まだ送信されない。
          2. 確認ダイアログ内の「アプローチを送る」ボタンをクリックして
             初めて、実際の送信処理（非同期）が開始される。

        v16までは手順1のみを実行しており、手順2の「アプローチを送る」を
        一度もクリックしていなかったため、実際には送信が確定していな
        かった（bot のログ上は成功に見えても、AirWork側では未送信の
        ままだった）。v17では手順2を明示的に追加した。

        ★ v21 変更点:
        手順1のボタン取得〜クリックは `_locate_and_click_bulk_button()`
        に切り出し、`StaleElementReferenceException` が起きても
        リトライして復帰できるようにした（詳細は当該メソッドの
        docstring、およびファイル冒頭の v21 変更点を参照）。

        手順2の後、送信は非同期に処理されるため、
          まとめてアプローチを送信中... → [更新して状況を確認する]
        という処理中表示になる。`_read_success_message()` 内で
        「更新して状況を確認する」ボタンを繰り返しクリックしながら、
        本物の成功通知（送信完了）が表示されるまで待つ（最大60秒）。
          * 通知が確認できた場合: その内容（タイトル・送信日時）を
            OK レベルでログ出力する。これは bot の自己申告ではなく、
            AirWork 側が実際に処理を受け付けたことを示す確認材料となる。
          * 「アプローチを送る」ボタンが見つからなかった場合、または
            timeoutまでに通知が確認できなかった場合は、実際に送信が
            完了したかどうか不明であるとして、WARN レベルでログ出力し、
            後ほど AirWork 上で実際の送信状況を確認するよう促す。
        通知の有無にかかわらず、処理自体は従来どおり続行する
        （一括送信のフロー自体は止めない）。

        ★ v26補足: 末尾のヘッダー再表示待ちループ（最大15秒）はあくまで
        「見た目上ボタンが戻ってくるまでのおおまかな猶予」であり、
        処理中表示が完全に解消した（＝checkboxが再度有効になった）ことの
        確定的な保証ではない。次バッチの選択操作の前には、必ず
        `_send_bulk_approach()` 側で `_wait_until_not_processing()` を
        呼んで確定的に確認するため、本メソッド自体のロジックは変更して
        いない。

        ★ v47 変更点（重大バグ修正）:
        従来、手順2の「アプローチを送る」ボタンのクリックに失敗した場合
        （`_click_confirm_send_button()` が False を返した場合）でも
        本メソッドは `True` を返していた。これにより、実際には送信が
        確定していないバッチが `_send_bulk_approach()` 側で
        `total_sent` に加算されてしまい、結果として送信していないのに
        「対応済み」と誤判定されるリスクがあった（詳細はファイル冒頭の
        v47 変更点コメントを参照）。
        v47では、この場合に `False` を返すように修正した。これにより
        `_send_bulk_approach()` は正しくこのバッチを送信済みとして
        計上せず、バッチ送信を打ち切る。`_process_row()` 側は
        `sent < limit` と正しく判定し、「確認必要」として人手の確認に
        回されるようになる。
        """
        if not self._locate_and_click_bulk_button():
            # ★ v18: 2回目以降のバッチで見つからないケースの原因調査用に、
            #   その時点のHTML/スクリーンショットを保存しておく。
            self._dump_debug_snapshot("bulk_button_not_found")
            return False

        time.sleep(1.0)

        # ★ v17: 確認ダイアログの「アプローチを送る」ボタンを押して
        #   送信を確定させる。これを押さない限り、実際には何も送信され
        #   ていない状態のままになる。
        # ★ v47: 従来はここで失敗しても True を返していたが、実際には
        #   送信が確定していないため、送信済みとして誤カウントされない
        #   よう False を返すように修正した。
        if not self._click_confirm_send_button(timeout=10.0):
            self._last_bulk_issue = (
                "確認ダイアログの「アプローチを送る」ボタンが見つからず、"
                "送信を確定できませんでした"
            )
            self._log(
                "確認ダイアログの「アプローチを送る」ボタンが見つかりませんでした。"
                "実際には送信が確定していないため、このバッチは送信済みとして"
                "計上しません。AirWork上で確認画面が表示されているか確認して"
                "ください。",
                "ERROR",
            )
            return False

        time.sleep(1.0)

        result = self._read_success_message(timeout=60.0, poll_interval=2.0)
        if result and result.get("title"):
            self._log(
                f"AirWork側の送信完了通知を確認しました: "
                f"「{result['title']}」 {result.get('date_text', '')}",
                "OK",
            )
        else:
            self._log(
                "「アプローチを送る」ボタンはクリックできましたが、"
                "60秒待ってもAirWork側の送信完了通知（送信完了）が"
                "確認できませんでした。実際に送信されているか、"
                "後ほどAirWork上で確認することをお勧めします。",
                "WARN",
            )

        # ★ v20: 送信完了のトースト通知が消えた後も、ヘッダー部分
        #   （"すべて選択" チェックボックスの隣、通常は「まとめてアプローチ」
        #   ボタンが表示される位置）が「処理中...更新して状況を確認する」の
        #   ままスタックしてしまうケースがあることが、実際のスクリーン
        #   ショットで確認された。この表示は自動的には元に戻らず、
        #   その場の「更新して状況を確認する」リンクを明示的にクリックしない
        #   限り「まとめてアプローチ」ボタンが再表示されない。
        #   v18では単に最大10秒「待つ」だけだったが、それでは表示が
        #   永久にスタックしたままになるため、v20では
        #   「まとめてアプローチ」ボタンが現れるまで、処理中表示があれば
        #   その都度「更新して状況を確認する」を能動的にクリックし続ける
        #   ループに変更した（最大15秒、1.5秒間隔）。
        #   ★ v26補足: このループは「見た目のボタン再表示」を軽く待つ
        #   だけのものであり、15秒で解消しなくても致命的ではない
        #   （後段の `_wait_until_not_processing()` が確定的に待つため）。
        header_deadline = time.time() + 15.0
        while time.time() < header_deadline:
            if self._stopped():
                break
            try:
                self.driver.find_element(
                    By.XPATH, "//button[contains(., 'まとめてアプローチ')]"
                )
                break
            except NoSuchElementException:
                pass

            if self._is_processing():
                self._click_refresh_status_button()

            time.sleep(1.5)

        return True

    def _count_candidates_on_page(self) -> int:
        return len(
            self.driver.find_elements(
                By.XPATH, "//input[contains(@data-la,'jobseekers_checkbox_click')]"
            )
        )

    def _go_to_next_candidate_page(self) -> bool:
        """
        次ページへ遷移する。

        ★ v24変更点: 遷移後の待機を、固定1.2秒 → document.readyState
        待ち＋短いハイドレーション猶予＋候補者カード（またはそれに代わる
        空表示メッセージ）が実際に描画されるまでのポーリング待ちに強化した。

        従来の固定1.2秒だけでは、次ページの候補者一覧（50件、各候補者
        カードにスキルタグ等の重いDOMを含む）が完全に描画・ハイドレート
        される前に後続の「すべて選択」クリックが行われてしまい、
        `_select_all_checkbox()` 側の docstring に記載した
        ハイドレーション未完了レースコンディションを誘発しやすかった。

        戻り値: 次ページへの遷移を試みた（＝「次へ」リンクが有効で
                クリックできた）場合は True。「次へ」ボタンが無効
                （＝最終ページに到達済み）、またはボタン自体が
                見つからない場合は False。
        """
        try:
            next_li = self.driver.find_element(
                By.XPATH,
                "//li[contains(@class,'paginateItem')][.//a[contains(@class,'next')]]",
            )
            if next_li.get_attribute("data-disabled") == "true":
                return False
            next_btn = next_li.find_element(By.XPATH, ".//a[contains(@class,'next')]")
            self.driver.execute_script("arguments[0].click();", next_btn)

            try:
                self._wait(15).until(
                    lambda d: d.execute_script("return document.readyState")
                    == "complete"
                )
            except TimeoutException:
                pass
            time.sleep(0.8)  # ハイドレーション猶予

            # 候補者カード（またはそれに代わる空表示メッセージ）が
            # 実際に描画されるまで待つ。
            self._wait_for_candidates_or_empty(timeout=10.0)
            time.sleep(0.5)

            return True
        except NoSuchElementException:
            return False

    def _select_candidates_for_batch(self, remaining: int, available: int) -> int:
        """
        次バッチ分の候補者チェックボックスを選択する。

        戻り値: 選択を試みた人数（take）。

        ★ v23で追加。
        従来は `_select_all_checkbox()` / `_select_individual_checkboxes()`
        を1回呼ぶだけで、実際に選択がUIへ反映された（＝「まとめてアプローチ」
        ボタンの disabled が外れた）かどうかを確認していなかった。

        実運用で、前バッチの送信完了通知が表示された直後に連続して次の
        選択操作を行うと、選択操作自体はエラーなく実行できたように
        見えても、非同期の再描画とタイミングが競合して選択状態が
        反映されない（ボタンが disabled のまま）ケースが確認された。
        この状態のままボタンを探しに行くと、実際には「処理中」でも
        何でもなく、単に「何も選択されていないので永久に disabled」な
        だけなので、どれだけ待っても解消しない。

        本メソッドは選択後に `_wait_for_bulk_button_enabled()` で
        実際に有効化されたかを確認し、有効化されていなければ選択操作を
        数回リトライする。

        ★ v26補足: 「候補者チェックボックス自体が処理中は disabled に
        なっている」ケースについては、本メソッドが呼ばれる前に
        `_send_bulk_approach()` 側で `_wait_until_not_processing()` に
        より処理中状態を解消してから呼び出すようにしたため、本メソッド
        内のリトライは「(b) 選択したのにUI反映が遅れているだけ」の
        本来のケースに対してのみ機能する想定になった。
        """
        if remaining < 50:
            planned_take = min(remaining, available)
            select_fn = lambda: self._select_individual_checkboxes(planned_take)
        elif remaining == 50 or available <= 50:
            planned_take = min(remaining, available)
            select_fn = self._select_all_checkbox
        else:  # remaining > 50 and available > 50 -> ページ単位で50人ずつ
            planned_take = min(50, available)
            select_fn = self._select_all_checkbox

        for attempt in range(1, 4):
            select_fn()
            if self._wait_for_bulk_button_enabled(timeout=5.0):
                # ★ v28: 「まとめてアプローチ」ボタンが有効になった＝
                #   少なくとも1件は選択されているが、実際に何件選択されて
                #   いるかは事前の見積もり（planned_take）と一致するとは
                #   限らない（特に _select_all_checkbox は「1ページ=50件」
                #   という前提が崩れた場合、想定より多い／少ない人数を
                #   選択してしまう可能性がある）。DOM上で実際に
                #   チェックされている件数を数え、見積もりと食い違って
                #   いればログに残した上で、実際の件数を返り値として使う
                #   （total_sent の記録をAirWork側の実態に合わせるため）。
                actual = self._count_checked_candidate_checkboxes()
                if actual <= 0:
                    # ボタンが有効なのにチェック数が0件として取得できない
                    # 場合は、セレクタの取りこぼしの可能性があるため、
                    # 安全側として見積もり値にフォールバックする。
                    actual = planned_take
                elif actual != planned_take:
                    self._log(
                        f"選択されたチェックボックス数（実際: {actual}人）が"
                        f"見積もり（{planned_take}人）と異なります。"
                        "実際の選択数を送信人数の記録に使用します。",
                        "WARN",
                    )
                return actual

            self._log(
                "チェックボックスを選択しましたが「まとめてアプローチ」ボタンが"
                "有効になりませんでした（選択が反映されていない可能性があります）。"
                f"選択をやり直して再試行します（{attempt}/3）...",
                "WARN",
            )
            time.sleep(0.8)

        self._log(
            "チェックボックスの選択を複数回試みましたが、"
            "「まとめてアプローチ」ボタンが有効になりませんでした。",
            "WARN",
        )
        self._dump_debug_snapshot("selection_not_reflected")
        return 0

    def _send_bulk_approach(self, limit_str: str) -> int:
        """
        G列のアプローチ上限数に応じて候補者を選択し、まとめてアプローチする。
        実際に送信完了が確認できた合計人数を返す。

        ★ v18: 何らかの理由（「まとめてアプローチ」ボタンが見つからない等）
        で途中で処理を打ち切った場合、戻り値の合計は G列の要求数
        （limit）より少なくなることがある。呼び出し側（_process_row）は
        この戻り値と limit を比較し、要求数に届かなかった場合は
        「対応済み」ではなく「確認必要」として人手による確認に回すこと。

        ★ v23: チェックボックスの選択が実際にUIへ反映された（＝
        「まとめてアプローチ」ボタンが disabled でなくなった）ことを
        `_select_candidates_for_batch()` で確認してから
        `_click_bulk_approach_button()` を呼ぶように変更した。選択が
        最終的に反映されなかった場合はそのバッチを送信せずに打ち切る
        （目標人数に届かなければ呼び出し側で「確認必要」に回される）。

        ★ v25: 現在ページの候補者数が0件と判定された場合、従来は即座に
        `break` して処理全体を終了していた。これだと、ページ送り直後の
        描画タイミングのブレなどにより一時的に0件と誤判定された場合や、
        たまたま現在ページだけ0件で次ページ以降にはまだ候補者が残って
        いる場合に、本来まだ探索すべきページを確認せずに処理を打ち切って
        しまう問題があった。
        v25では、現在ページが0件と判定された場合はまず
        `_go_to_next_candidate_page()` で次ページへの遷移を試み、
          * 遷移できた場合（＝「次へ」がまだ有効だった場合）は
            ループの先頭に戻って新しいページで候補者数を再判定する。
          * 遷移できなかった場合（＝「次へ」が disabled、つまり最後の
            ページまで確認し終えた場合）は、これ以上探すページが無い
            ため、従来どおり `break` して処理を終了する。
        `_go_to_next_candidate_page()` はページの終端で確実に `False`
        を返すため、無限ループには陥らない。

        ★ v26: 選択操作の前に `_wait_until_not_processing()` を呼び、
        前バッチの「まとめてアプローチを送信中...」処理中表示（＝候補者
        チェックボックスが disabled になっている状態）が解消するのを
        確定的に待ってから、次バッチの選択に進むようにした。処理中表示が
        タイムアウトしても解消しない場合は、無意味な選択リトライを
        繰り返さずにそのバッチ送信を打ち切り、「確認必要」として人手に
        よる確認に回す（詳細はファイル冒頭の v26 変更点を参照）。

        ★ v29: どの `break` で処理を打ち切ったのかを
        `self._last_bulk_issue` に記録するようにした。呼び出し側
        （_process_row）は sent < limit の場合、この理由を
        「確認必要」のステータスセルに併記する。

        ★ v47: `_click_bulk_approach_button()` が「アプローチを送る」
        ボタンをクリックできなかった場合に False を返すよう修正した
        ことに伴い、下の `else` 分岐（既存のログ・
        `self._last_bulk_issue` 設定処理）がこのケースでも正しく
        機能するようになった。`_send_bulk_approach()` 自体のロジックは
        変更していない。
        """
        self._last_bulk_issue = ""

        try:
            limit = int(re.sub(r"\D", "", limit_str)) if limit_str else 0
        except ValueError:
            limit = 0

        if limit <= 0:
            self._log("アプローチ上限数が未設定/不正のためスキップします。", "WARN")
            return 0

        total_sent = 0
        remaining = limit

        while remaining > 0:
            if self._stopped():
                self._last_bulk_issue = "ユーザー操作により処理が停止されました"
                break

            available = self._count_candidates_on_page()
            if available == 0:
                # ★ v19: ページ送り直後や検索直後は候補者カードの描画が
                #   一瞬遅れることがあるため、即座に0件と判定して抜けず、
                #   短時間ポーリングして再確認する。
                if self._wait_for_candidates_or_empty(timeout=8.0):
                    available = self._count_candidates_on_page()

                if available == 0:
                    # ★ v25: 現在ページで0件が確定した場合も、即座に
                    #   処理を打ち切らず、まず次ページへの遷移を試みる。
                    #   「次へ」が無効（最終ページ到達済み）の場合のみ
                    #   これ以上探すページが無いとみなして打ち切る。
                    self._log(
                        "現在のページには候補者が表示されていません。"
                        "次のページへ遷移して確認します...",
                        "INFO",
                    )
                    if self._go_to_next_candidate_page():
                        continue
                    else:
                        self._last_bulk_issue = (
                            "候補者一覧の最終ページまで確認しましたが"
                            "対象者が不足していました"
                        )
                        self._log(
                            "これ以上先のページが無いため、候補者の探索を"
                            "終了します。"
                            f"これまでに確認できた送信済み合計: {total_sent}人"
                            f"（目標: {limit}人）。",
                            "WARN",
                        )
                        break

            # ★ v26: 前バッチの「まとめてアプローチを送信中...」処理中
            #   表示（＝候補者チェックボックスが disabled になっている
            #   状態）が残ったまま次の選択操作に入ってしまうと、選択操作
            #   自体が無効化されており、何度リトライしても「まとめて
            #   アプローチ」ボタンが有効にならない。選択の前に必ず
            #   処理中表示が解消するのを確定的に待つ。
            if not self._wait_until_not_processing(timeout=60.0):
                self._last_bulk_issue = (
                    "前バッチの送信処理中表示が60秒待っても解消しませんでした"
                )
                self._log(
                    "前バッチの処理中表示（まとめてアプローチを送信中...）が"
                    "60秒待っても解消しなかったため、これ以上のバッチ送信を"
                    "中断します。"
                    f"これまでに確認できた送信済み合計: {total_sent}人"
                    f"（目標: {limit}人）。",
                    "WARN",
                )
                break

            # 処理中表示が解消した直後は候補者一覧の描画が更新されて
            # いる可能性があるため、選択対象の人数を念のため再取得する。
            available = self._count_candidates_on_page()
            if available == 0:
                if self._wait_for_candidates_or_empty(timeout=8.0):
                    available = self._count_candidates_on_page()
                if available == 0:
                    self._last_bulk_issue = (
                        "処理中表示の解消後、候補者が表示されなくなりました"
                    )
                    self._log(
                        "処理中表示の解消後、候補者が表示されなくなったため、"
                        "候補者の探索を終了します。"
                        f"これまでに確認できた送信済み合計: {total_sent}人"
                        f"（目標: {limit}人）。",
                        "WARN",
                    )
                    break

            take = self._select_candidates_for_batch(remaining, available)
            if take <= 0:
                self._last_bulk_issue = (
                    "候補者チェックボックスの選択が反映されず"
                    "「まとめてアプローチ」ボタンが有効になりませんでした"
                )
                self._log(
                    f"候補者の選択に失敗したため、これ以上のバッチ送信を中断します。"
                    f"これまでに確認できた送信済み合計: {total_sent}人"
                    f"（目標: {limit}人）。",
                    "WARN",
                )
                break

            if self._click_bulk_approach_button():
                total_sent += take
                remaining -= take
            else:
                self._last_bulk_issue = (
                    "「まとめてアプローチ」ボタンが見つからず送信できませんでした"
                )
                self._log(
                    f"「まとめてアプローチ」ボタンが見つからなかったため、"
                    f"このバッチ（{take}人分）は送信できませんでした。"
                    f"これまでに確認できた送信済み合計: {total_sent}人"
                    f"（目標: {limit}人）。",
                    "WARN",
                )
                break

            if remaining <= 0:
                break

            # 次ページがあれば継続。無ければ終了（対象者不足）。
            if not self._go_to_next_candidate_page():
                self._last_bulk_issue = "次ページが無いため対象者が不足しました"
                break

        return total_sent

    # ─────────────────────────────────────────────────────────────
    #  1行分の処理
    # ─────────────────────────────────────────────────────────────
    def _process_row(self, row_idx: int, row: List[str], attempt: int = 1):
        """
        ★ v33: `attempt` 引数を追加した。
        `run()` の自動リトライパスから呼ばれた場合、現在何回目の試行かが
        渡される（1 = 初回、2以上 = 自動リトライ）。
        「候補者を探す」ボタンが操作不可＋掲載中、という一時的問題の
        可能性がある状況で、最終試行（attempt >= RETRY_MAX_ATTEMPTS）
        でもなお解消しない場合にステータスの扱いを変えるために使う
        （詳細は当該分岐のコメントを参照）。
        """
        company = _col(row, COL_COMPANY)
        air_id = _col(row, COL_AIRID)
        password = _col(row, COL_PASS)
        # ★ v29: 全角数字・不可視文字混入によるコピペずれを吸収するため、
        #   シートから読み込んだ求人番号を正規化する。
        job_id = _normalize_job_id(_col(row, COL_JOBID))
        limit_str = _col(row, COL_LIMIT)

        conditions = {
            "希望勤務地":   _col(row, COL_H),
            "最終学歴":     _col(row, COL_I),
            "年以降":       _col(row, COL_J),
            "年以前":       _col(row, COL_K),
            "年齢下限":     _col(row, COL_L),
            "年齢上限":     _col(row, COL_M),
            "スキル":       _col(row, COL_N),
            "経験":         _col(row, COL_O),
            "保有資格":     _col(row, COL_P),
            "英会話レベル": _col(row, COL_Q),
        }
        has_conditions = any(v for v in conditions.values())

        self._log(f"── 行{row_idx}: {company} / 求人番号={job_id} を処理します。", "INFO")

        if not air_id or not password:
            self._log(f"行{row_idx}: AirID/パスワードが未入力のためスキップします。", "WARN")
            return

        if self._current_air_id != air_id:
            self._login(air_id, password)
            self._current_air_id = air_id

        self._note_login_time(row_idx)

        if not self._search_job_id_on_candidates_page(job_id):
            self._log(f"行{row_idx}: 求人番号 {job_id} が見つかりませんでした。", "WARN")
            self._update_status(row_idx, STATUS_JOB_NOT_FOUND)
            self._record_result(STATUS_JOB_NOT_FOUND, row_idx, company, job_id, attempt=attempt)
            return

        result, job_type_text = self._try_click_find_candidates(job_id)

        # ★ v29: 「候補者を探す」リンクが inactive（クリック不可）だった
        #   場合の分岐。従来は STATUS_NEED_CONFIRM に更新するだけで理由が
        #   分からなかったため、掲載状況（job_offers画面）の結果に応じて
        #   具体的な理由をステータスセルに併記するようにした。
        if result == "inactive":
            if job_type_text and job_type_text != "正社員":
                reason = f"雇用形態：{job_type_text}"
                # ★ v34: シート上は「正社員以外」のみとし、シートが煩雑に
                #   ならないようにする。ただし詳細な雇用形態は
                #   `_record_result` には渡しておき、Chatworkへの報告
                #   （サマリー内の詳細セクション）でのみ表示する。
                self._update_status(row_idx, STATUS_NOT_FULLTIME)
                self._record_result(STATUS_NOT_FULLTIME, row_idx, company, job_id, reason, attempt=attempt)
                return

            pub_status = self._check_job_offer_publish_status(job_id)
            if pub_status == "未掲載":
                self._update_status_with_reason(row_idx, STATUS_UNPUBLISHED)
                self._record_result(STATUS_UNPUBLISHED, row_idx, company, job_id, attempt=attempt)
                return

            if pub_status is None:
                reason = (
                    "「候補者を探す」ボタンが表示されない/クリックできない状態でした"
                    "（job_offers画面で掲載状況を確認できませんでした）"
                )
                self._log(f"行{row_idx}: {reason}", "WARN")
                self._update_status_with_reason(row_idx, STATUS_NEED_CONFIRM, reason)
                self._record_result(STATUS_NEED_CONFIRM, row_idx, company, job_id, reason, attempt=attempt)
                return

            reason = (
                "「候補者を探す」ボタンが表示されない/クリックできない状態でした"
                f"（求人一覧の掲載状況：{pub_status}）"
            )

            # ★ v33: 「掲載中」なのに「候補者を探す」ボタンが操作不可、
            #   という状況はAirWork側の一時的な表示不整合の可能性がある
            #   ため、通常は「確認必要」として自動リトライの対象にする。
            #   しかし RETRY_MAX_ATTEMPTS 回試してもなお同じ状況が続く
            #   場合は、一時的な問題ではなく実質的に候補者を提示できない
            #   状態が続いていると判断し、ステータスを
            #   「候補者を表示できません」に切り替えて以降の自動リトライ
            #   対象から外す（_run_pass はSTATUS_NEED_CONFIRMの行だけを
            #   リトライ対象にするため）。
            #   ただし、Chatworkへの報告では原因が「掲載中なのにボタンが
            #   押せない」ことだと分かるよう、この詳細な理由文言はそのまま
            #   維持してシート・Chatworkの両方に残す。
            if pub_status == "掲載中" and attempt >= RETRY_MAX_ATTEMPTS:
                self._log(
                    f"行{row_idx}: {reason}"
                    f"（{RETRY_MAX_ATTEMPTS}回試行しても解消しなかったため、"
                    "「候補者を表示できません」として処理を終了します）",
                    "WARN",
                )
                self._update_status_with_reason(row_idx, STATUS_NO_CANDIDATES, reason)
                self._record_result(STATUS_NO_CANDIDATES, row_idx, company, job_id, reason, attempt=attempt)
                return

            self._log(f"行{row_idx}: {reason}", "WARN")
            self._update_status_with_reason(row_idx, STATUS_NEED_CONFIRM, reason)
            self._record_result(STATUS_NEED_CONFIRM, row_idx, company, job_id, reason, attempt=attempt)
            return

        # result == "clicked" → 候補者検索画面が開いている
        # ★ v28: 固定 sleep(1.5) だけでは、回線やサーバー負荷次第で
        #   ページ描画が間に合わないタイミングがあり、条件未入力時の
        #   「デフォルト画面に候補者がいるか」の判定
        #   （_count_candidates_on_page() == 0）を実際より早く行って
        #   しまい、無条件検索フォールバックが不要に発動することがあった。
        #   他の待機処理（_click_condition_search_button 等）と同様に
        #   document.readyState 待ち＋ハイドレーション猶予に変更する。
        try:
            self._wait(15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            pass
        time.sleep(1.5)

        if has_conditions:
            # v6: _apply_conditions は検索実行後にフィルターバーの適用条件を
            #     確認し、入力した条件がすべて反映されていれば True、
            #     反映されていない疑いがある（＝検索ボタンが見つからなかった
            #     場合を含む）場合は False を返す。
            #     False の場合は誤った対象へアプローチを送ってしまうことを
            #     避けるため、チェックボックスの選択・一括アプローチ送信には
            #     進まず、「確認必要」として人手による確認に回す。
            # ★ v29: 具体的な理由を self._last_condition_issue から取得し、
            #     ステータスセルに併記する。
            conditions_ok = self._apply_conditions(conditions)
            if not conditions_ok:
                reason = self._last_condition_issue or "検索条件の適用に失敗しました"
                self._log(f"行{row_idx}: {reason}", "WARN")
                self._update_status_with_reason(row_idx, STATUS_NEED_CONFIRM, reason)
                self._record_result(STATUS_NEED_CONFIRM, row_idx, company, job_id, reason, attempt=attempt)
                return
        else:
            # ★ v8: 検索条件が一切入力されていない場合。
            #   まずは「候補者を探す」クリック直後のデフォルト画面に、
            #   候補者のチェックボックスが表示されているかを確認する。
            if self._count_candidates_on_page() == 0 and not self._check_no_candidates_message(timeout=2.0):
                # チェックボックスも空表示メッセージも無い＝UI側がまだ
                # 一覧を描画していない中間状態の可能性が高いため、
                # 「条件で候補者を探す」→ 無条件のまま「検索する」を
                # 実行して一覧を表示させるフォールバックを試みる。
                self._log(
                    f"行{row_idx}: 検索条件が未入力で、デフォルトの候補者一覧も"
                    "表示されていないため、無条件検索を実行します。",
                    "INFO",
                )
                if not self._search_with_no_conditions():
                    # ★ v29: 具体的な理由をステータスセルに併記する。
                    reason = (
                        "検索条件未入力のため無条件検索を試みましたが、"
                        "モーダルまたは「検索する」ボタンが見つかりませんでした"
                    )
                    self._log(f"行{row_idx}: {reason}", "WARN")
                    self._update_status_with_reason(row_idx, STATUS_NEED_CONFIRM, reason)
                    self._record_result(STATUS_NEED_CONFIRM, row_idx, company, job_id, reason, attempt=attempt)
                    return

                # v8: 無条件検索を実行してもなお候補者が1件も表示されない
                #     場合（空表示メッセージが出た場合も、単に0件だった
                #     場合も含む）は、無意味な一括アプローチ処理へ進まない
                #     よう、専用ステータスに更新して終了する。
                # ★ v35: 原因が「本当に候補者がいない」のか「1日の送信
                #     上限に達しているだけ」なのかを、シート記録から
                #     判定して振り分ける。
                if self._count_candidates_on_page() == 0:
                    resolved_status, resolved_reason = self._decide_no_candidates_status(
                        row_idx, air_id
                    )
                    self._log(
                        f"行{row_idx}: 無条件検索を実行しても候補者が表示されません"
                        f"でした（{resolved_status}）。",
                        "WARN",
                    )
                    self._update_status_with_reason(row_idx, resolved_status)
                    self._record_result(
                        resolved_status, row_idx, company, job_id,
                        resolved_reason, attempt=attempt,
                    )
                    return

        # ★ v19: 検索条件適用直後は、フィルターバー（適用条件・件数）が
        #   先に表示され、実際の候補者カード（チェックボックス）の描画が
        #   数秒遅れることがある。この描画待ちをせずに次のチェックへ進むと、
        #   実際には候補者がいるのに「0件」と誤判定してしまうため、ここで
        #   一度、候補者カードが表示されるか空表示メッセージが出るまで
        #   ポーリングして待つ。
        self._wait_for_candidates_or_empty(timeout=15.0)

        # ★ v7: 条件検索の有無に関わらず、一括アプローチ送信の直前に
        #   「候補者を表示できませんでした」という空表示メッセージが
        #   出ていないかを確認する。検索条件に合致する候補者がいない、
        #   または手動アプローチの上限に既に達している場合にこの
        #   メッセージが表示されるため、その場合は無意味な一括送信処理を
        #   行わずに専用ステータスへ更新して終了する。
        # ★ v35: どちらが原因かをシート記録から判定して振り分ける。
        if self._check_no_candidates_message():
            resolved_status, resolved_reason = self._decide_no_candidates_status(
                row_idx, air_id
            )
            self._log(
                f"行{row_idx}: 「候補者を表示できませんでした」というメッセージを検知しました"
                f"（{resolved_status}と判定）。",
                "WARN",
            )
            self._update_status_with_reason(row_idx, resolved_status)
            self._record_result(resolved_status, row_idx, company, job_id, resolved_reason, attempt=attempt)
            return

        sent = self._send_bulk_approach(limit_str)
        self._note_sent_count(row_idx, sent)

        # ★ v18: 送信できた人数が G列の要求数（limit）に届かなかった場合、
        #   実際には途中で処理が打ち切られている（例: 「まとめてアプローチ」
        #   ボタンが見つからず早期終了）ため、「対応済み」と誤って確定させず
        #   「確認必要」として人手による確認に回すようにした。
        # ★ v29: 具体的な理由を self._last_bulk_issue から取得し、
        #   ステータスセルに併記する。
        try:
            limit = int(re.sub(r"\D", "", limit_str)) if limit_str else 0
        except ValueError:
            limit = 0

        if limit > 0 and sent < limit:
            base_reason = self._last_bulk_issue or "原因不明のまま送信が目標人数に届きませんでした"
            reason = f"送信済み{sent}人／目標{limit}人。{base_reason}"
            self._log(
                f"行{row_idx}: 目標{limit}人に対し{sent}人しか送信を確認できな"
                "かったため、「確認必要」として処理を終了します。",
                "WARN",
            )
            write_ok = self._update_status_with_reason(row_idx, STATUS_NEED_CONFIRM, reason)
            self._record_result(
                STATUS_NEED_CONFIRM, row_idx, company, job_id, reason,
                attempt=attempt, sent_count=sent,
            )
            if not write_ok and sent > 0:
                # ★ v30: シート更新失敗＋送信済みあり＝重複送信リスクが
                #   ある重大ケース。サマリー通知（run終了時）を待たず、
                #   即座にChatworkで報告する。
                critical_detail = (
                    f"{sent}人に実際にアプローチを送信済みですが、シートの"
                    "ステータスを更新できませんでした。このままだと次回実行時に"
                    "同じ候補者へ重複してアプローチが送信される可能性があるため、"
                    "スプレッドシートのA列を手動で「確認必要」に更新してください。"
                )
                self._log(
                    f"★重要: 行{row_idx}（{company} / 求人番号={job_id}）は"
                    f"{critical_detail}",
                    "ERROR",
                )
                self._notifier.notify_critical_error(
                    title="シート更新失敗（重複送信リスク）",
                    company=company,
                    job_id=job_id,
                    row_idx=row_idx,
                    detail=critical_detail,
                    sheet_url=self.current_sheet_url,
                )
            return

        write_ok = self._update_status(row_idx, STATUS_DONE)
        self._record_result(STATUS_DONE, row_idx, company, job_id, attempt=attempt)
        if not write_ok:
            # ★ v30: こちらも重複送信リスクがある重大ケースのため、
            #   サマリー通知を待たず即座にChatworkで報告する。
            critical_detail = (
                f"{sent}人に実際にアプローチを送信済みですが、シートの"
                "ステータスを『対応済み』に更新できませんでした。このままだと"
                "次回実行時に同じ候補者へ重複してアプローチが送信される"
                "可能性があるため、スプレッドシートのA列を手動で"
                "「対応済み」に更新してください。"
            )
            self._log(
                f"★重要: 行{row_idx}（{company} / 求人番号={job_id}）は"
                f"{critical_detail}",
                "ERROR",
            )
            self._notifier.notify_critical_error(
                title="シート更新失敗（重複送信リスク）",
                company=company,
                job_id=job_id,
                row_idx=row_idx,
                detail=critical_detail,
                sheet_url=self.current_sheet_url,
            )
        self._log(f"行{row_idx}: {sent}人にアプローチを送信し、対応済みにしました。", "OK")

    # ─────────────────────────────────────────────────────────────
    #  メイン実行
    # ─────────────────────────────────────────────────────────────
    def run(self):
        self._stop_flag = False
        # ★ v46で修正（重要なバグ）。
        # 従来は run() の先頭で無条件に `self._run_stats` /
        # `self._last_report_body` をリセットしていた。これにより、
        # 「1回目の実行で全行を正常に処理し終えた後、（確認・再確認の
        # つもりで）もう一度『実行』を押したところ、対応必要の行が
        # 1件も無かったため何も処理されずに終わった」というケースで、
        # 1回目の実行結果（＝本来なら「報告を送信」で送れるはずだった
        # 内容）が2回目の実行開始時点で問答無用に消去されてしまい、
        # 結果として「全行処理し終えたのに報告を送信ボタンが押せない」
        # という不具合が発生していた。
        #
        # v46では、リセット前の状態を `_previous_run_stats` /
        # `_previous_report_body` として保持しておき、今回の run() が
        # 実際には1行も処理せずに終わった場合（シート取得失敗、対象データ
        # 無し、対応必要の行が0件、のいずれか）は、リセットを取り消して
        # 前回の実行結果をそのまま復元する。これにより、「何もすることが
        # ない」だけの実行によって、既に完了している前回の報告可能な
        # 結果が失われることがなくなる。
        _previous_run_stats = self._run_stats
        _previous_report_body = self._last_report_body

        self._run_stats = self._new_run_stats()
        self._last_report_body = None

        def _restore_previous_report(reason: str):
            """
            今回のrun()が実質何もしなかった場合に、リセットを取り消して
            前回の報告可能な結果を復元する。

            2つの条件を両方満たす場合のみ復元する:
              1. 前回そもそも報告可能な結果があった
                （`_previous_run_stats["total"] > 0`）
              2. 今回のrun()が実際には1行も処理していない
                （`self._run_stats["total"] == 0`）
            条件2が無いと、「対象行の取得後、処理の途中で予期しない
            エラーが発生した」ようなケースで、今回の実行で既に得られて
            いた（たとえ部分的でも本物の）処理結果を、古い前回の結果で
            上書きして消してしまうことになるため、これを防ぐ。
            """
            if not _previous_run_stats or _previous_run_stats.get("total", 0) == 0:
                return
            if self._run_stats.get("total", 0) != 0:
                return
            self._run_stats = _previous_run_stats
            self._last_report_body = _previous_report_body
            self._log(
                f"{reason}前回の実行結果（報告可能なデータ）は"
                "そのまま保持されています。「報告を送信」から送信"
                "できます。",
                "INFO",
            )

        try:
            self._log("手動アプローチ処理を開始します...", "INFO")
            self._open_target_worksheet()

            # ★ v39: 起動直後のシート全体読み込みがネットワーク不調で
            #   無期限にブロックするのを防ぐ。
            all_values = self._run_with_timeout(
                self.target_ws.get_all_values,
                timeout=30.0,
                description="処理対象行の読み込みのためのシート取得",
            )
            if all_values is None:
                self._log(
                    "シートの読み込みに失敗した（タイムアウト/ネットワーク"
                    "エラー）ため、処理を中止します。",
                    "ERROR",
                )
                _restore_previous_report("シート読み込みに失敗したため、")
                return
            if len(all_values) <= 1:
                self._log("対象データが見つかりませんでした。", "WARN")
                _restore_previous_report("対象データが無かったため、")
                return

            data_rows = all_values[1:]  # header を除く
            target_rows: List[Tuple[int, List[str]]] = []
            for offset, row in enumerate(data_rows):
                status = _col(row, COL_STATUS)
                if status != STATUS_NEED:
                    continue
                row_idx = offset + 2  # スプレッドシートは1始まり + ヘッダー行
                target_rows.append((row_idx, row))

            self._run_stats["total"] = len(target_rows)

            if not target_rows:
                self._log("処理対象（対応必要）の行がありません。", "WARN")
                _restore_previous_report("対応必要の行が無かったため、")
                return

            # ── 1回目の処理 ──────────────────────────────────────
            self._log(f"{len(target_rows)}件を処理します（1回目）...", "INFO")
            self._run_pass(target_rows, attempt=1)

            # ── ★ v31: 自動リトライパス ──────────────────────────
            # 「確認必要」になった行は一時的な問題（AirWork側の非同期処理・
            # UI描画タイミングのズレ等）が原因のことが多いため、Chatworkへ
            # 最終報告する前に自動で再挑戦し、それでも解決しない行だけを
            # 最終的な「要確認」として残す。
            # 「求人ID見つからない」等の構造的な結果はリトライ対象外
            #（_run_pass 内で row_results の status を見て絞り込む）。
            for attempt in range(2, RETRY_MAX_ATTEMPTS + 1):
                if self._stopped():
                    break

                retry_targets = [
                    (row_idx, row)
                    for row_idx, row in target_rows
                    if self._run_stats["row_results"].get(row_idx, {}).get("status")
                    == STATUS_NEED_CONFIRM
                ]
                if not retry_targets:
                    break

                self._log(
                    f"「確認必要」と判定された{len(retry_targets)}件を"
                    f"自動的に再試行します（{attempt}回目）...",
                    "INFO",
                )
                time.sleep(RETRY_WAIT_SECONDS)
                self._run_pass(retry_targets, attempt=attempt)

            self._log("手動アプローチ処理が完了しました。", "OK")
        except Exception as e:
            self._log(f"致命的エラー: {e}", "ERROR")
            self._log(traceback.format_exc(), "ERROR")
            # ★ v46: このrun()が実質何も処理できなかった場合
            #  （例: _open_target_worksheet() が早期に失敗した等）は、
            #   前回の報告可能な結果を消さずに復元する。実際に処理が
            #   始まった後のエラーであれば、`_restore_previous_report`
            #   内のガードにより何もしない（今回の部分的な結果を守る）。
            _restore_previous_report("実行中に致命的エラーが発生したため、")
        finally:
            # ★ v42: 自動リトライを使い切れないまま処理が中断された
            #  （ユーザーの停止操作・予期しないエラー等）「確認必要」の
            #   行を検出し、「対応必要」に戻す。normal終了・異常終了
            #   どちらの場合でも確実に行われるよう finally の先頭で行う。
            #   ベストエフォート（失敗してもrun()全体は継続する）。
            try:
                self._revert_interrupted_need_confirm_rows()
            except Exception as e:
                self._log(
                    f"中断された「確認必要」行の差し戻し処理中にエラーが"
                    f"発生しました: {e}",
                    "WARN",
                )

            # ★ v40: 従来はここで自動的に `_send_run_summary()` を呼び、
            #   run() 終了と同時にChatworkへ実行結果を送信していた。
            #   しかし実際の運用では、run() 終了直後はまだユーザーが
            #   シートの「確認必要」行を目視確認・修正する前の状態で
            #   あり、この時点で送ってしまうと報告内容がその後の手直しと
            #   食い違ってしまう問題があった。
            #   v40では自動送信をやめ、GUI側の「📮 報告を送信」ボタンから
            #   `preview_report_text()` → `send_report()` を明示的に
            #   呼び出す方式に変更した（ユーザーが確認・修正した後の
            #   "今のシートの状態" を反映してから送信できるようにする
            #   ため）。ここでは `self._run_stats` を保持したままにする
            #   ことで、後からGUI経由で報告を組み立てられるようにする。
            if self._run_stats and self._run_stats.get("total", 0) > 0:
                self._log(
                    "実行結果の報告はまだChatworkへ送信されていません。"
                    "シートの内容を確認後、「報告を送信」から送信してください。",
                    "INFO",
                )
            self.close()

    def _run_pass(self, targets: List[Tuple[int, List[str]]], attempt: int = 1):
        """
        ★ v31で追加、v33で `attempt` を追加。
        指定された行のリストを順に `_process_row()` で処理する。
        `run()` の初回パス、および「確認必要」行の自動リトライパスの
        両方から共通で呼び出される。`attempt` は現在何回目の試行かを
        `_process_row()` に伝えるためのもの（1=初回）。
        """
        for row_idx, row in targets:
            if self._stopped():
                self._log("停止リクエストにより処理を中断しました。", "WARN")
                break
            try:
                self._process_row(row_idx, row, attempt=attempt)
            except Exception as e:
                self._log(f"行{row_idx}の処理中にエラー: {e}", "ERROR")
                self._log(traceback.format_exc(), "ERROR")
                # ★ v30: _process_row が例外で丸ごと失敗した行も、
                #   サマリー上は「確認必要」扱いとして記録しておく
                #   （シート側のステータスは変更されていない可能性が
                #   高いため、実際の値は次回実行時に確認されるが、
                #   ユーザーには今回の実行で何が起きたか伝わるように
                #   する）。次のリトライパスでも自動的に再挑戦の対象になる。
                self._record_result(
                    STATUS_NEED_CONFIRM,
                    row_idx,
                    _col(row, COL_COMPANY),
                    _col(row, COL_JOBID),
                    f"処理中に例外が発生しました: {e}",
                    attempt=attempt,
                )

    def _revert_interrupted_need_confirm_rows(self):
        """
        ★ v42で追加。
        自動リトライの仕組み（RETRY_MAX_ATTEMPTS 回まで試す）は、
        「確認必要」になった行をChatworkへ報告する前に自動的に
        再挑戦することで、一時的な問題（AirWork側の非同期処理・UI
        描画タイミングのズレ等）による誤報を減らすためのものである。

        しかし実運用で、ユーザーの停止操作や予期しないエラーにより、
        RETRY_MAX_ATTEMPTS 回のリトライを消化しきる前に処理全体が
        中断されるケースが確認された。この場合、該当の行はたまたま
        中断された時点での最後の試行結果（＝多くの場合1回目の失敗）が
        シートに残ったまま「確認必要」として固定されてしまう。

        「確認必要」の行は `run()` の最初でシートから拾われる対象
        （ステータスが「対応必要」の行）には含まれないため、次回の
        run()でも自動的には再試行されず、ユーザーが手動でA列を
        「対応必要」に書き換えない限り、永久にリトライされないまま
        放置されてしまう問題があった。

        本メソッドは、`run()` の全処理（初回パス＋自動リトライパス）が
        終わった直後に呼び出す。`self._run_stats["row_results"]` を
        確認し、「確認必要」のまま残っている行のうち、その行が
        確定した時点の試行回数（`attempt`）が `RETRY_MAX_ATTEMPTS`
        未満だった行（＝フルにリトライしきれないまま中断された行）を
        検出し、シート上のステータスを「対応必要」に戻す。これにより、
        次回のrun()でこれらの行が自然に拾われ、自動的に再試行される
        ようになる。

        `attempt` が `RETRY_MAX_ATTEMPTS` に達している行（＝リトライを
        使い切った上でなお「確認必要」と判断された行）は対象外とし、
        従来どおり「確認必要」のまま残す（本当に人手の確認が必要な
        行を自動的に握りつぶさないため）。

        ★ v43で追加（重要な安全策）:
        `attempt` に関わらず、その行の処理で1人でも実際にAirWorkへ
        送信できたことが確認されている行（`sent_count > 0`）は、
        絶対に自動で「対応必要」へ戻さない。詳細は下の for ループ内の
        コメントを参照。一部でも送信済みの行を自動的に再試行対象へ
        戻すと、次回の run() が「今回何人送信済みか」を知らないまま
        改めてG列の上限数までフルに送信を試みてしまい、候補者への
        重複アプローチや、意図した1日の送信上限を超えた送信につながる
        重大なリスクがあるため、この種の行は必ず人手の確認を経由させる。
        """
        row_results: Dict[int, Dict[str, object]] = self._run_stats.get(
            "row_results", {}
        )
        reverted_rows: List[int] = []
        failed_to_revert: List[int] = []
        excluded_partial_send_rows: List[int] = []

        for row_idx, r in row_results.items():
            if r.get("status") != STATUS_NEED_CONFIRM:
                continue

            # ★ v43で追加（重要な安全策）。
            # 一部でも実際にAirWorkへ送信済み（sent_count > 0）の行は、
            # たとえリトライ回数が RETRY_MAX_ATTEMPTS 未満であっても
            # 絶対に自動で「対応必要」へ戻さない。
            #
            # 理由: 自動的に「対応必要」へ戻すと、次回の run() で
            # その行が改めて対応必要として拾われ、
            # `_send_bulk_approach()` が「今回何人送信したか」の記憶を
            # 持たないままG列の上限数までフルに送信を試みてしまう。
            # 結果として、
            #   (a) 前回既に送信した候補者に対して再度アプローチが
            #       送信されてしまう（重複アプローチ）恐れがある、
            #   (b) T列（送信人数）は追記ではなく上書きのため、前回分の
            #       送信人数が記録から失われ、1日の送信上限
            #      （`DAILY_APPROACH_LIMIT_PER_COMPANY`）の判定
            #      （`_get_company_sent_total_today()`）が当日の実際の
            #       送信数より少なく計算されてしまい、意図せず1日の
            #       上限を超えて送信し続けてしまう恐れがある。
            # これらは実際に候補者へアプローチが飛んでしまう重大な
            # リスクのため、送信が絡む行は必ず人手の確認を経てから
            # 「対応必要」に戻すべきであり、bot が自動的に判断しては
            # ならない。
            if r.get("sent_count", 0) > 0:
                excluded_partial_send_rows.append(row_idx)
                continue

            last_attempt = r.get("attempt", 0) or 0
            if last_attempt >= RETRY_MAX_ATTEMPTS:
                # リトライを使い切った上での「確認必要」。人手確認が
                # 必要な行なので触らない。
                continue

            ok = self._update_status(row_idx, STATUS_NEED)
            if ok:
                reverted_rows.append(row_idx)
            else:
                failed_to_revert.append(row_idx)

        if reverted_rows:
            self._log(
                f"リトライが完了しないまま中断された{len(reverted_rows)}件の"
                "行を「対応必要」に戻しました（次回実行時に自動的に"
                "再試行されます）: "
                + ", ".join(f"行{i}" for i in reverted_rows),
                "INFO",
            )
        if failed_to_revert:
            self._log(
                "以下の行は「対応必要」への差し戻しに失敗しました。"
                "「確認必要」のまま残っている可能性があるため、"
                "手動で確認してください: "
                + ", ".join(f"行{i}" for i in failed_to_revert),
                "WARN",
            )
        if excluded_partial_send_rows:
            self._log(
                f"以下の{len(excluded_partial_send_rows)}件は一部の候補者に"
                "既にアプローチを送信済みのため、リトライが未完了でも"
                "自動的な「対応必要」への差し戻しを行いませんでした"
                "（重複送信を避けるため、必ず人手で確認してください）: "
                + ", ".join(f"行{i}" for i in excluded_partial_send_rows),
                "WARN",
            )

    def _build_final_sheet_tally(self) -> Optional[Dict[str, object]]:
        """
        ★ v37で追加。
        run() の全処理・自動リトライが完了した後にシート全体を改めて
        読み直し、現在シートに実際に書かれているステータスを行ごとに
        集計する。

        なぜ必要か:
          従来の集計（`self._run_stats["row_results"]`）は、bot が
          「今回のrun()で対応必要として実際に処理した行」だけを対象に
          していた。しかしシートには、過去の実行で既に対応済みになった
          行や、ユーザーが手動で対応してステータスを書き換えた行も
          多数存在する。上司への報告はシート全体の現状を反映すべき
          であり、「bot が今回何件処理したか」だけでは不十分
          （例：シート全体401行のうち、bot が今回対応必要として処理した
          のは343行だけで、残り58行は既に手動対応済みだったとしても、
          上司への報告には401行分の内訳が反映されるべき）。

        列Aの値は「確認必要（理由）」のように理由が括弧書きで付与されて
        いることがあるため、"（" より前の部分を基本ステータスとして
        分類に使う。

        bot が今回処理した行については `row_results` に詳細な理由
        （reason）が残っているため、それを優先して使う。bot が今回
        処理していない行（＝手動で設定された行）は理由を持たないため、
        シート側の括弧内テキストがあればそれを使い、無ければ
        「（手動で設定されたステータスです）」を使う。

        戻り値: 集計結果の辞書。シート取得に失敗した場合は None。
        """
        # ★ v39: 全行の処理・自動リトライが完了した直後に呼ばれるこの
        #   シート再取得が、ネットワーク不調時に無期限にブロックして
        #   bot がフリーズしたまま応答しなくなる事象が報告された
        #  （停止ボタンを押しても反応しない状態になっていた）。
        #   タイムアウトガード経由に変更し、既定30秒で諦めて None を
        #   返すようにした（呼び出し側の `_send_run_summary()` は
        #   None の場合、Chatworkへの通知をスキップしてログにWARNを
        #   残すだけで、bot 全体の終了処理は止めずに先へ進む）。
        all_values = self._run_with_timeout(
            self.target_ws.get_all_values,
            timeout=30.0,
            description="最終集計のためのシート再取得",
        )
        if all_values is None:
            return None

        data_rows = all_values[1:]
        row_results: Dict[int, Dict[str, str]] = self._run_stats.get("row_results", {})

        counts: Dict[str, int] = defaultdict(int)
        need_confirm_rows: List[Dict[str, str]] = []
        no_candidates_detail_rows: List[Dict[str, str]] = []
        not_fulltime_detail_rows: List[Dict[str, str]] = []

        for offset, row in enumerate(data_rows):
            row_idx = offset + 2
            raw_status = _col(row, COL_STATUS)
            if not raw_status:
                counts["(空欄)"] += 1
                continue

            base_status = raw_status.split("（", 1)[0].strip()
            counts[base_status] += 1

            company = _col(row, COL_COMPANY)
            job_id = _col(row, COL_JOBID)
            bot_reason = row_results.get(row_idx, {}).get("reason", "")

            if base_status == STATUS_NEED_CONFIRM:
                if bot_reason:
                    reason = bot_reason
                elif "（" in raw_status and raw_status.endswith("）"):
                    reason = raw_status.split("（", 1)[1][:-1]
                else:
                    reason = "（手動で設定されたステータスです）"
                need_confirm_rows.append(
                    {
                        "row_idx": row_idx,
                        "company": company,
                        "job_id": job_id,
                        "reason": reason,
                    }
                )
            elif base_status == STATUS_NO_CANDIDATES and bot_reason:
                no_candidates_detail_rows.append(
                    {
                        "row_idx": row_idx,
                        "company": company,
                        "job_id": job_id,
                        "reason": bot_reason,
                    }
                )
            elif base_status == STATUS_NOT_FULLTIME and bot_reason:
                not_fulltime_detail_rows.append(
                    {
                        "row_idx": row_idx,
                        "company": company,
                        "job_id": job_id,
                        "reason": bot_reason,
                    }
                )

        need_confirm_rows.sort(key=lambda item: item["row_idx"])
        no_candidates_detail_rows.sort(key=lambda item: item["row_idx"])
        not_fulltime_detail_rows.sort(key=lambda item: item["row_idx"])

        return {
            "total_in_sheet": len(data_rows),
            "counts": counts,
            "need_confirm_rows": need_confirm_rows,
            "no_candidates_detail_rows": no_candidates_detail_rows,
            "not_fulltime_detail_rows": not_fulltime_detail_rows,
        }

    def _build_report_body(self) -> Optional[str]:
        """
        ★ v30で追加、v31/v35/v37で更新、v40で「送信しない・本文だけ返す」
        形に変更した（旧 `_send_run_summary`）。

        シート全体を再読み込みして集計し、Chatworkへ送る報告本文
        （生のテキスト。test_mode表記は含まない）を組み立てて返す。
        送信自体はこのメソッドの責務ではない
        （GUIの「報告を送信」フローでは `preview_report_text()` /
        `send_report()` から呼び出される。run() 終了時の自動送信は
        v40で廃止した）。

        bot が今回処理対象とした行が0件だった場合（＝対応必要の行が
        1つも無かった場合）や、シート再取得に失敗した場合は None を
        返す。
        """
        stats = self._run_stats
        if not stats or stats.get("total", 0) == 0:
            return None

        tally = self._build_final_sheet_tally()
        if tally is None:
            self._log(
                "シート全体の最終集計に失敗したため、報告内容を作成できません。",
                "WARN",
            )
            return None

        counts: Dict[str, int] = tally["counts"]
        total_in_sheet: int = tally["total_in_sheet"]
        bot_processed_count: int = stats["total"]

        done_count = counts.get(STATUS_DONE, 0)
        job_not_found_count = counts.get(STATUS_JOB_NOT_FOUND, 0)
        no_candidates_count = counts.get(STATUS_NO_CANDIDATES, 0)
        no_matching_candidates_count = counts.get(STATUS_NO_MATCHING_CANDIDATES, 0)
        not_fulltime_count = counts.get(STATUS_NOT_FULLTIME, 0)
        unpublished_count = counts.get(STATUS_UNPUBLISHED, 0)
        # ★ v37: 「対応必要」のまま残っている行（＝bot が今回停止された、
        #   AirID/パスワード未入力でスキップされた等により未処理のまま
        #   残っている行）も上司に分かるように件数化する。
        still_pending_count = counts.get(STATUS_NEED, 0)

        need_confirm_rows = tally["need_confirm_rows"]
        no_candidates_detail_rows = tally["no_candidates_detail_rows"]
        not_fulltime_detail_rows = tally["not_fulltime_detail_rows"]

        # ★ v32/v37: 既知のカテゴリ・空欄のいずれにも属さない行
        #  （想定外の文字列がA列に入っている等）を「その他/未処理」として
        #   明示する。
        known_base_statuses = {
            STATUS_DONE,
            STATUS_JOB_NOT_FOUND,
            STATUS_NO_CANDIDATES,
            STATUS_NO_MATCHING_CANDIDATES,
            STATUS_NOT_FULLTIME,
            STATUS_UNPUBLISHED,
            STATUS_NEED,
            STATUS_NEED_CONFIRM,
            "(空欄)",
        }
        other_count = sum(
            c for status, c in counts.items() if status not in known_base_statuses
        )

        try:
            return self._notifier.build_summary_body(
                total_in_sheet=total_in_sheet,
                bot_processed_count=bot_processed_count,
                done_count=done_count,
                need_confirm_rows=need_confirm_rows,
                job_not_found_count=job_not_found_count,
                no_candidates_count=no_candidates_count,
                no_matching_candidates_count=no_matching_candidates_count,
                not_fulltime_count=not_fulltime_count,
                unpublished_count=unpublished_count,
                still_pending_count=still_pending_count,
                other_count=other_count,
                no_candidates_detail_rows=no_candidates_detail_rows,
                not_fulltime_detail_rows=not_fulltime_detail_rows,
                sheet_url=self.current_sheet_url,
            )
        except Exception as e:
            self._log(f"報告内容の作成に失敗しました: {e}", "WARN")
            return None

    # ─────────────────────────────────────────────────────────────
    #  ★ v40で追加: GUIの「📮 報告を送信」ボタンから呼ばれる公開API
    # ─────────────────────────────────────────────────────────────
    def has_report_available(self) -> bool:
        """
        GUIが「報告を送信」ボタンを有効化してよいかどうかを判定するために
        呼ぶ。直近の run() が1件以上の行を処理対象とした場合に True。
        """
        return bool(self._run_stats and self._run_stats.get("total", 0) > 0)

    def preview_report_text(self) -> Optional[str]:
        """
        ★ v40で追加。
        GUIの「報告を送信」ボタンが押された際、まずこれを呼び出す。
        シートの最新状態を読み直して報告本文を組み立て、実際に
        Chatworkへ送信されるのとまったく同じテキスト（test_modeの
        テスト表記が有効ならそれも含む）を返す。

        組み立てた生の本文は `self._last_report_body` にキャッシュする。
        続けて `send_report()` が呼ばれた場合はこのキャッシュされた
        本文をそのまま送信するため、ここで表示したプレビューと実際に
        送信される内容が完全に一致することが保証される（sendの直前に
        本文を作り直さない）。

        戻り値: プレビュー用テキスト。作成に失敗した場合は None。
        """
        body = self._build_report_body()
        if body is None:
            self._last_report_body = None
            return None
        self._last_report_body = body
        try:
            return self._notifier.render_preview(body)
        except Exception as e:
            self._log(f"報告内容のプレビュー作成に失敗しました: {e}", "WARN")
            return None

    def send_report(self) -> bool:
        """
        ★ v40で追加。
        直前の `preview_report_text()` 呼び出しでキャッシュされた本文
        （`self._last_report_body`）を、そのままChatworkへ送信する。
        何らかの理由でキャッシュが無い場合（＝ `preview_report_text()`
        を経由せずに直接呼ばれた場合等）は、念のためこの場で本文を
        組み立ててから送信する。

        戻り値: 送信に成功すれば True。
        """
        body = self._last_report_body
        if body is None:
            body = self._build_report_body()
            if body is None:
                return False

        try:
            return self._notifier.send_prebuilt(body)
        except Exception as e:
            self._log(f"Chatworkへの報告送信に失敗しました: {e}", "ERROR")
            return False
