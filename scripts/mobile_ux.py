"""Regression coverage for shared sticky controls, receipt uploads and app dialogs."""
import base64
from playwright.sync_api import expect

PHOTO = {"name": "receipt.png", "mimeType": "image/png", "buffer": base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aS1sAAAAASUVORK5CYII=")}


def login(page, url, admin=False):
    page.goto(url)
    if admin:
        value = page.locator('#account option').evaluate_all(
            "options => options.find(o => o.textContent.includes('Administrator')).value")
        page.select_option('#account', value)
    page.get_by_role('button', name='Enter FuelTrack').click()


def nav(page, name):
    if page.locator('.menu-toggle').is_visible():
        page.get_by_role('button',name='Open navigation menu',exact=True).click()
        page.locator('.drawer-nav').get_by_role('button',name=name,exact=False).click()
    else:
        page.locator('.nav').get_by_role('button',name=name,exact=False).click()
    page.evaluate('scrollTo(0,0)')


def assert_no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), page.evaluate("()=>({width:innerWidth,title:document.querySelector('h1').textContent,overflow:[...document.querySelectorAll('.main *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,10).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right}))})")


def run_mobile_ux(browser, url):
    errors = []
    for width in [320, 375, 390, 430, 700, 1024, 1280]:
        height = {320: 568, 375: 667, 390: 844, 430: 932}.get(width, 900)
        for admin in [False, True]:
            context = browser.new_context(viewport={"width": width, "height": height}, is_mobile=width <= 700, has_touch=width <= 700)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('dialog', lambda dialog: errors.append('Unexpected native dialog: '+dialog.message) or dialog.dismiss())
            login(page, url, admin)
            page.locator('.range-trigger').first.click()
            page.get_by_role('button',name='Past 12 months',exact=True).click()
            page.get_by_role('button',name='Apply range').click()
            from responsive_navigation import check_navigation
            check_navigation(page, admin, width)
            views = ['Overview', 'Receipts'] + (['Reports', 'Team'] if admin else [])
            for view in views:
                nav(page, view)
                assert_no_overflow(page)
                from responsive_navigation import check_lists
                check_lists(page, view, admin, width)
                if width <= 700:
                    stack = page.locator('.mobile-workspace')
                    expect(stack).to_have_count(1)
                    initial = stack.bounding_box()['y']
                    for scroll in [200, 550, 1000]:
                        page.evaluate('(y)=>scrollTo(0,y)', scroll)
                        page.wait_for_timeout(40)
                        box = stack.bounding_box()
                        if page.evaluate('scrollY') >= initial:
                            assert abs(box['y']) < 1, (width, admin, view, box)
                        assert stack.evaluate("e=>getComputedStyle(e).backgroundColor") == 'rgb(245, 247, 250)'
                        header = stack.locator('.top').bounding_box()
                        toolbar = stack.locator('.sticky-filters,.report-sticky')
                        if toolbar.count():
                            bar = toolbar.bounding_box()
                            assert abs(header['y']+header['height']-bar['y']) < 1, (view, header, bar)
                            assert toolbar.evaluate("e=>getComputedStyle(e).backgroundColor") == 'rgb(245, 247, 250)'
                            assert bar['y']+bar['height'] <= height, (view, bar)
                        # The header paints across both viewport edges, sealing side gaps.
                        if abs(box['y']) < 1:
                            assert page.evaluate("document.elementFromPoint(1,2).closest('.mobile-workspace') !== null")
                    if view == 'Overview':
                        secondary = page.locator('.card > .sticky-filters')
                        expect(secondary).to_have_count(1)
                        assert secondary.evaluate("e=>getComputedStyle(e).position") == 'static'
                    if view == 'Reports':
                        page.get_by_role('button', name='Filters ▾').click()
                        expect(page.get_by_role('button', name='Close filters ▴')).to_have_attribute('aria-expanded','true')
                        assert_no_overflow(page)
                        page.locator('#reportFilterControls .multi-trigger').first.click()
                        assert_no_overflow(page)
                        page.get_by_role('button', name='Close filters ▴').click()
                else:
                    expect(page.locator('.mobile-workspace')).to_have_count(0)
                    assert page.locator('.top').evaluate("e=>getComputedStyle(e).position") == 'sticky'
            # Resizing restores nested desktop toolbar placement, then integrates it again.
            nav(page, 'Receipts')
            page.set_viewport_size({"width": 1280, "height": 844})
            expect(page.locator('.card > .sticky-filters')).to_have_count(1)
            page.set_viewport_size({"width": 390, "height": 844})
            expect(page.locator('.mobile-workspace > .sticky-filters')).to_have_count(1)
            page.locator('.range-trigger').first.click()
            page.locator('#pickerFrom').fill('')
            page.locator('#pickerTo').fill('')
            page.locator('#pickerFrom').dispatch_event('change')
            page.locator('#pickerTo').dispatch_event('change')
            page.get_by_role('button', name='Apply range').click()
            expect(page.locator('.app-notice.error')).to_contain_text('Select both')
            page.keyboard.press('Escape')
            expect(page.locator('dialog[open]')).to_have_count(0)
            context.close()
    assert not errors, errors
    run_receipt_workflows(browser, url)
    from responsive_navigation import run_responsive_workflows
    run_responsive_workflows(browser,url)
    print('PASS: employee Overview/Receipts; admin Overview/Receipts/Reports/Team at 320,375,390,430,700,1024,1280px; sticky scroll, wrapping, resize, dialogs; no JS errors')


def run_receipt_workflows(browser, url):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('dialog', lambda dialog: errors.append('Unexpected native dialog: '+dialog.message) or dialog.dismiss())
    login(page, url)
    page.get_by_role('button', name='+ Add receipt').click()
    for label, input_id, capture in [('Take Photo', 'receiptCamera', 'environment'), ('Choose Existing Photo or File','receiptImage', None)]:
        with page.expect_file_chooser() as chooser:
            page.get_by_role('button', name=label, exact=True).click()
        assert chooser.value.element.get_attribute('id') == input_id
        assert chooser.value.element.get_attribute('capture') == capture
        # Dismissing a chooser produces no change; zero files must not clear a preview.
        page.locator('#'+input_id).dispatch_event('cancel')
    page.locator('#receiptCamera').set_input_files(PHOTO)
    expect(page.locator('#imagePreview img')).to_be_visible()
    first_preview = page.locator('#imagePreview img').get_attribute('src')
    page.locator('#receiptImage').dispatch_event('cancel')
    assert page.locator('#imagePreview img').get_attribute('src') == first_preview
    count_before_cancel = page.evaluate('data.receipts.length')
    page.keyboard.press('Escape')
    expect(page.locator('dialog[open]')).to_have_count(0)
    assert page.evaluate('data.receipts.length') == count_before_cancel
    page.get_by_role('button',name='+ Add receipt').click()
    expect(page.locator('#imagePreview img')).to_have_count(0)
    page.locator('#receiptImage').set_input_files(PHOTO)
    expect(page.locator('#imagePreview img')).to_be_visible()
    page.locator('#receiptImage').set_input_files({"name":"bad.txt","mimeType":"text/plain","buffer":b'not an image'})
    expect(page.locator('#uploadFeedback')).to_contain_text('supported image')
    assert page.locator('#imagePreview img').get_attribute('src') == first_preview
    page.locator('#receiptImage').set_input_files({"name":"broken.png","mimeType":"image/png","buffer":b'broken'})
    expect(page.locator('#uploadFeedback')).to_contain_text('could not be opened')
    page.locator('#receiptImage').set_input_files(PHOTO)
    expect(page.locator('#uploadFeedback')).to_have_text('')
    page.get_by_role('button', name='Submit receipt', exact=True).dispatch_event('click')
    expect(page.locator('#receiptFormFeedback')).to_contain_text('Enter a valid total amount')
    page.locator('#famount').fill('30000')
    page.locator('#fstation').fill('shell')
    page.locator('#flocation').fill('Newark')
    page.get_by_role('button', name='Newark, NJ', exact=True).click()
    before_confirmation = page.evaluate('data.receipts.length')
    page.get_by_role('button', name='Submit receipt', exact=True).click()
    confirm = page.get_by_role('dialog',name='Check receipt amount')
    expect(confirm).to_be_visible()
    expect(confirm.get_by_role('button',name='Cancel')).to_be_focused()
    page.keyboard.press('Shift+Tab')
    assert page.evaluate("document.activeElement.closest('.app-dialog') !== null")
    page.keyboard.press('Escape')
    expect(page.locator('#famount')).to_be_focused()
    expect(page.locator('#imagePreview img')).to_be_visible()
    assert page.evaluate('data.receipts.length') == before_confirmation
    before = page.evaluate('data.receipts.length')
    page.locator('#famount').fill('4862')
    # A failed write keeps the form/photo and does not claim a successful submission.
    page.evaluate("()=>{window.originalSetItem=Storage.prototype.setItem;Storage.prototype.setItem=()=>{throw new Error('quota')}}")
    page.get_by_role('button',name='Submit receipt',exact=True).click()
    expect(page.locator('.app-notice.error')).to_contain_text('Could not save')
    assert page.evaluate('data.receipts.length') == before
    expect(page.locator('#imagePreview img')).to_be_visible()
    page.evaluate('()=>{Storage.prototype.setItem=window.originalSetItem}')
    page.get_by_role('button',name='Submit receipt',exact=True).click()
    success=page.get_by_role('dialog',name='Receipt submitted')
    expect(success).to_be_visible()
    assert page.evaluate('data.receipts.length') == before+1
    receipt_id=page.evaluate('data.receipts[0].id')
    success.get_by_role('button',name='View receipt').click()
    expect(page.get_by_role('dialog',name='Receipt details')).to_be_visible()
    page.keyboard.press('Escape')
    # Verify persistence and admin status confirmations on the same local demo data.
    page.evaluate('logout()')
    value=page.locator('#account option').evaluate_all("options=>options.find(o=>o.textContent.includes('Administrator')).value")
    page.select_option('#account',value)
    page.get_by_role('button',name='Enter FuelTrack').click()
    page.evaluate('(id)=>openReceipt(id)',receipt_id)
    for status in ['Approved','Rejected','Paid','Pending']:
        page.get_by_role('dialog',name='Receipt details').get_by_role('button',name=status,exact=True).click()
        dialog=page.get_by_role('dialog',name='Confirm status change')
        expect(dialog).to_be_visible()
        if status=='Pending': expect(dialog).to_contain_text('will NOT reverse')
        page.keyboard.press('Escape')
        assert page.evaluate('(id)=>data.receipts.find(r=>r.id===id).status',receipt_id) != status
        page.get_by_role('dialog',name='Receipt details').get_by_role('button',name=status,exact=True).click()
        page.get_by_role('dialog',name='Confirm status change').get_by_role('button',name='Mark '+status).click()
        expect(page.locator('.modal .pill')).to_have_text(status)
        assert page.evaluate('(id)=>data.receipts.find(r=>r.id===id).audit.length',receipt_id) > 1
    page.keyboard.press('Escape')
    nav(page,'Team')
    page.get_by_role('button',name='Deactivate',exact=True).first.click()
    page.get_by_role('dialog',name='Deactivate merchandiser?').get_by_role('button',name='Cancel').click()
    expect(page.get_by_role('dialog')).to_have_count(0)
    page.get_by_role('button',name='Deactivate',exact=True).first.click()
    page.get_by_role('dialog',name='Deactivate merchandiser?').get_by_role('button',name='Deactivate',exact=True).click()
    page.get_by_role('button',name='Reactivate',exact=True).first.click()
    page.get_by_role('dialog',name='Reactivate merchandiser?').get_by_role('button',name='Reactivate',exact=True).click()
    page.get_by_role('button',name='+ Add merchandiser').click()
    page.locator('#newName').fill('Mobile Test Employee')
    page.get_by_role('button',name='Add employee',exact=True).click()
    expect(page.get_by_text('Mobile Test Employee',exact=True)).to_be_visible()
    assert not errors, errors
    context.close()
    # Success offers a separate dashboard return action as well.
    context=browser.new_context(viewport={"width":320,"height":568})
    page=context.new_page();login(page,url)
    page.get_by_role('button',name='+ Add receipt').click()
    page.locator('#receiptImage').set_input_files(PHOTO)
    expect(page.locator('#imagePreview img')).to_be_visible()
    page.locator('#famount').fill('30000');page.locator('#fstation').fill('Shell')
    page.locator('#flocation').fill('Newark');page.get_by_role('button',name='Newark, NJ',exact=True).click()
    page.get_by_role('button',name='Submit receipt',exact=True).click()
    page.get_by_role('dialog',name='Check receipt amount').get_by_role('button',name='Submit receipt',exact=True).click()
    page.get_by_role('dialog',name='Receipt submitted').get_by_role('button',name='Return to dashboard').click()
    expect(page.get_by_role('heading',name='My fuel dashboard',exact=True)).to_be_visible()
    context.close()
    print('PASS: separate camera/file choices, upload cancellation/errors/preview, validation, storage failure, successful submission, safe async status changes and audit, team controls, dialog Escape/focus')
