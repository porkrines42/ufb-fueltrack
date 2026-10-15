"""Mobile navigation, receipt presentation and chart interaction regressions."""
from playwright.sync_api import expect


def check_navigation(page, admin, width):
    menu = page.get_by_role('button',name='Open navigation menu',exact=True)
    if width > 700:
        expect(menu).to_be_hidden()
        expect(page.locator('.side')).to_be_visible()
        return
    expect(menu).to_be_visible()
    expect(page.locator('.side')).to_be_hidden()
    assert page.locator('.mobile-appbar img').evaluate('e=>e.complete && e.naturalWidth>0')
    menu.click()
    drawer = page.get_by_role('dialog',name='FuelTrack menu')
    expect(drawer).to_be_visible()
    expect(menu).to_have_attribute('aria-expanded','true')
    assert page.locator('.drawer-nav button').count() == (4 if admin else 2)
    assert page.locator('.drawer-nav [aria-current="page"]').count() == 1
    expect(drawer.get_by_role('button',name='Log Out',exact=True)).to_be_visible()
    assert drawer.get_by_role('button',name='+ Add receipt',exact=True).count() == (0 if admin else 1)
    assert page.locator('html').evaluate('e=>getComputedStyle(e).overflow') == 'hidden'
    expect(drawer.get_by_role('button',name='Close navigation menu')).to_be_focused()
    page.keyboard.press('Shift+Tab')
    expect(drawer.get_by_role('button',name='Log Out',exact=True)).to_be_focused()
    page.keyboard.press('Tab')
    expect(drawer.get_by_role('button',name='Close navigation menu')).to_be_focused()
    page.keyboard.press('Escape')
    expect(drawer).to_have_count(0)
    expect(menu).to_be_focused()
    expect(menu).to_have_attribute('aria-expanded','false')
    menu.click()
    drawer.get_by_role('button',name='Close navigation menu').click()
    expect(menu).to_be_focused()
    menu.click()
    # Tap the backdrop outside the drawer panel.
    page.mouse.click(width-5,20)
    expect(drawer).to_have_count(0)
    expect(menu).to_be_focused()


def check_lists(page, view, admin, width):
    if width > 700:
        if view != 'Team':
            expect(page.locator('.mobile-receipts').first).to_be_hidden()
        return
    if view == 'Team':
        for button in page.locator('.userline > button').all():
            assert button.bounding_box()['height'] >= 44
        return
    container = page.locator('.main > .card').last if view=='Reports' else page.locator('#results' if view=='Receipts' else '#recentResults')
    cards = container.locator('.receipt-item')
    expected = page.evaluate("(view)=>view==='Receipts'?filteredReceipts().map(r=>r.id):view==='Reports'?[...reportRows()].sort((a,b)=>(b.createdAt||b.date).localeCompare(a.createdAt||a.date)).slice(0,100).map(r=>r.id):selected().filter(r=>employeeMatch(r)&&r.status!=='Rejected'&&matchesSearch(r,recentSearch)).sort((a,b)=>(b.createdAt||b.date).localeCompare(a.createdAt||a.date)).slice(0,8).map(r=>r.id)", view)
    assert cards.evaluate_all('cards=>cards.map(c=>c.dataset.receiptId)') == expected
    if expected:
        first = page.evaluate('(id)=>data.receipts.find(r=>r.id===id)',expected[0])
        card=cards.first
        expect(card.locator('h3')).to_have_text(first['station'])
        expect(card.locator('.receipt-location')).to_have_text(first['location'])
        expect(card.locator('.pill')).to_have_text(first['status'])
        assert card.locator('.receipt-employee').count() == (1 if admin else 0)
        assert card.locator('button').bounding_box()['height'] >= 44
        card.get_by_role('button').click()
        expect(page.get_by_role('dialog',name='Receipt details')).to_be_visible()
        assert page.get_by_role('dialog',name='Receipt details').get_by_role('button',name='Approved',exact=True).count() == (1 if admin and first['status']!='Approved' else 0)
        page.keyboard.press('Escape')
    expect(container.locator('.desktop-receipts')).to_be_hidden()
    if view=='Reports':
        summary=page.locator('.report-summary')
        assert summary.evaluate('e=>e.scrollWidth <= e.clientWidth+1')


def run_responsive_workflows(browser,url):
    from mobile_ux import login,nav,assert_no_overflow
    for admin in [False,True]:
        context=browser.new_context(viewport={'width':320,'height':568},is_mobile=True,has_touch=True)
        page=context.new_page();errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        login(page,url,admin)
        # Menu owns logout; the original mobile sidebar is no longer needed.
        page.get_by_role('button',name='Open navigation menu').click()
        if not admin:
            page.locator('.drawer-submit').click()
            expect(page.get_by_role('dialog',name='Upload gas receipt')).to_be_visible()
            expect(page.locator('.mobile-drawer')).to_have_count(0)
            page.keyboard.press('Escape')
        else:
            page.keyboard.press('Escape')
        # Legend toggles and all chart styles retain their data and readable geometry.
        page.locator('.stack-legend').filter(has_text='Rejected').click()
        assert page.evaluate('includeRejectedChart')
        for chart_type in ['bar','line','stacked']:
            page.get_by_label('Chart type',exact=True).select_option(chart_type)
            svg=page.locator('#spendingSVG')
            assert svg.bounding_box()['width'] <= 320
            assert svg.evaluate('e=>e.viewBox.baseVal.width') < 400
            assert_no_overflow(page)
        page.set_viewport_size({'width':1024,'height':900})
        expect(page.locator('#spendingSVG')).to_have_attribute('viewBox','0 0 720 285')
        page.set_viewport_size({'width':320,'height':568})
        expect(page.locator('#spendingSVG')).to_have_attribute('viewBox','0 0 258 240')
        page.locator('.stack-segment').first.tap()
        expect(page.locator('.stack-tooltip')).to_be_visible()
        page.locator('.stack-legend').filter(has_text='Pending').focus()
        expect(page.locator('.stack-tooltip')).to_be_visible()
        # Search/date/status filters update cards and the hidden desktop table together.
        nav(page,'Receipts')
        from filter_panel import set_date_range, panel_selection
        set_date_range(page)
        page.get_by_role('button',name='Filters',exact=True).click()
        panel=page.get_by_role('dialog',name='Filters',exact=True)
        panel.locator('#filterSearch').fill('Shell')
        panel.get_by_role('button',name='Apply Filters',exact=True).click()
        cards=page.locator('#results .receipt-item')
        assert cards.count()>0
        for card in cards.all():expect(card).to_contain_text('Shell')
        page.get_by_role('button',name='Filters',exact=True).click()
        panel.locator('#filterSearch').fill('no-such-station-123')
        panel.get_by_role('button',name='Apply Filters',exact=True).click()
        expect(cards).to_have_count(0)
        expect(page.locator('#results .mobile-receipts')).to_contain_text('No matching receipts')
        page.get_by_role('button',name='Filters',exact=True).click()
        panel.locator('#filterSearch').fill('')
        panel_selection(page,'status',['Pending'])
        panel.get_by_role('button',name='Apply Filters',exact=True).click()
        for pill in page.locator('#results .receipt-item .pill').all():expect(pill).to_have_text('Pending')
        check_lists(page,'Receipts',admin,320)
        # Long values are real-shaped test data in an isolated browser context only.
        page.evaluate("""()=>{const r=scoped()[0];r.station='VeryLongStationName'.repeat(8);r.location='A long city and street name '.repeat(8);r.amount=1234567.89;search='';period='all';multi.status=[];filterStatus='all';tab='receipts';render()}""")
        assert_no_overflow(page)
        check_lists(page,'Receipts',admin,320)
        # Drawer closes cleanly at a desktop breakpoint and restores normal navigation.
        page.get_by_role('button',name='Open navigation menu').click()
        page.set_viewport_size({'width':1024,'height':900})
        expect(page.locator('.mobile-drawer')).to_have_count(0)
        expect(page.locator('.side')).to_be_visible()
        expect(page.locator('.desktop-receipts')).to_be_visible()
        assert page.locator('html').evaluate('e=>getComputedStyle(e).overflow') != 'hidden'
        page.set_viewport_size({'width':375,'height':667})
        page.get_by_role('button',name='Open navigation menu').click()
        page.get_by_role('button',name='Log Out',exact=True).click()
        expect(page.get_by_role('button',name='Enter FuelTrack')).to_be_visible()
        assert page.evaluate('me===null')
        expect(page.locator('dialog[open]')).to_have_count(0)
        assert not errors,errors
        context.close()
    print('PASS: role-aware drawer, all dismissal methods, focus/scroll lock, logout, receipt cards/data/actions, search/filter/order, long values, chart styles and breakpoints')
