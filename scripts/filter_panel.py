"""Regression checks for transactional, nonsticky mobile filters."""
import csv
import io
from pathlib import Path
from playwright.sync_api import expect


def mobile_filters(page):
    return page.locator('.mobile-filter-launcher').is_visible()


def set_date_range(page, key='all'):
    if mobile_filters(page):
        page.get_by_role('button',name='Filters',exact=True).click()
        page.locator('#filterPeriod').select_option(key)
        page.get_by_role('button',name='Apply Filters',exact=True).click()
    else:
        page.locator('.range-trigger').first.click()
        labels={'all':'Past 12 months','month':'This month','week':'This week','lastmonth':'Last month'}
        page.get_by_role('button',name=labels[key],exact=True).click()
        page.get_by_role('button',name='Apply range').click()


def panel_selection(page,kind,values):
    group=page.locator(f'details[data-filter-type="{kind}"]')
    if not group.evaluate('e=>e.open'):group.locator('summary').click()
    group.get_by_role('button',name='Clear',exact=True).click()
    for value in values:
        group.locator('input').evaluate_all('(inputs,value)=>{const input=inputs.find(e=>e.value===value);input.click()}',value)


def check_mobile_panel(page,view,admin,width):
    launcher=page.locator('.mobile-filter-launcher')
    if width>700 or view=='Team':
        expect(launcher).to_have_count(0)
        return
    expect(launcher).to_be_visible()
    assert launcher.evaluate("e=>getComputedStyle(e).position")=='static'
    assert launcher.evaluate("e=>!e.closest('.mobile-workspace')")
    initial=launcher.bounding_box()['y'];initial_scroll=page.evaluate('scrollY')
    page.evaluate('scrollTo(0,200)')
    assert abs(launcher.bounding_box()['y']-(initial-(page.evaluate('scrollY')-initial_scroll)))<1
    launcher.get_by_role('button',name='Filters',exact=True).scroll_into_view_if_needed()
    old_y=page.evaluate('scrollY')
    before=page.evaluate('JSON.stringify(appliedFilterSnapshot())')
    launcher.get_by_role('button',name='Filters',exact=True).click()
    panel=page.get_by_role('dialog',name='Filters',exact=True)
    expect(panel).to_be_visible()
    expect(panel.get_by_role('button',name='Close filters',exact=True)).to_be_focused()
    assert page.locator('html').evaluate('e=>getComputedStyle(e).overflow')=='hidden'
    assert page.locator('body').evaluate('e=>getComputedStyle(e).position')=='fixed'
    bounds=panel.bounding_box()
    viewport=page.evaluate('({height:visualViewport.height,top:visualViewport.offsetTop})')
    assert bounds['height']<=viewport['height']+1
    assert bounds['y']>=viewport['top']-1
    assert bounds['y']+bounds['height']<=viewport['top']+viewport['height']+1
    footer=panel.locator('footer').bounding_box()
    assert footer['y']+footer['height']<=viewport['top']+viewport['height']+1
    assert panel.evaluate('e=>e.scrollWidth<=e.clientWidth+1')
    locked_top=page.locator('body').evaluate('e=>e.style.top')
    locked_scroll=page.evaluate('scrollY')
    page.mouse.move(20,20);page.mouse.wheel(0,400);page.wait_for_timeout(50)
    assert page.evaluate('scrollY')==locked_scroll
    assert page.locator('body').evaluate('e=>e.style.top')==locked_top
    form=panel.locator('form')
    if form.evaluate('e=>e.scrollHeight>e.clientHeight'):
        form.evaluate('e=>e.scrollTop=200')
        assert form.evaluate('e=>e.scrollTop')>0
    assert panel.locator('input[name="employee"]').count()==(page.evaluate("data.users.filter(u=>u.role==='merch').length") if admin else 0)
    assert bool(panel.locator('input[name="status"]').count())==(view!='Overview')
    assert bool(panel.locator('input[name="fuel"]').count())==(view=='Reports')
    panel.locator('#filterSearch').fill('unapplied search')
    panel.locator('#filterPeriod').select_option('lastmonth')
    assert page.evaluate('JSON.stringify(appliedFilterSnapshot())')==before
    page.keyboard.press('Escape')
    expect(panel).to_have_count(0)
    assert page.evaluate('JSON.stringify(appliedFilterSnapshot())')==before
    assert abs(page.evaluate('scrollY')-old_y)<1
    expect(launcher.get_by_role('button',name='Filters',exact=True)).to_be_focused()
    # All date operations use the same panel, including inline invalid-range errors.
    launcher.get_by_role('button',name='Filters',exact=True).click()
    panel.locator('#filterPeriod').select_option('custom')
    panel.locator('#filterFrom').fill('2026-10-15')
    panel.locator('#filterTo').fill('2026-10-01')
    panel.get_by_role('button',name='Apply Filters',exact=True).click()
    expect(panel.locator('#filterRangeError')).to_contain_text('on or before')
    assert page.evaluate('JSON.stringify(appliedFilterSnapshot())')==before
    panel.get_by_role('button',name='Close filters',exact=True).click()
    assert abs(page.evaluate('scrollY')-old_y)<1


def run_filter_workflows(browser,url):
    from mobile_ux import login,nav,assert_no_overflow
    for admin in [False,True]:
        context=browser.new_context(viewport={'width':375,'height':667},is_mobile=True,has_touch=True)
        page=context.new_page();errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        login(page,url,admin)
        for view in ['Overview','Receipts']+(['Reports'] if admin else []):
            nav(page,view)
            set_date_range(page,'allDates')
            target=page.evaluate('scoped().find(r=>r.status==="Pending")||scoped()[0]')
            page.get_by_role('button',name='Filters',exact=True).click()
            panel=page.get_by_role('dialog',name='Filters',exact=True)
            if admin:panel_selection(page,'employee',[target['userId']])
            if view!='Overview':panel_selection(page,'status',[target['status']])
            if view=='Reports':panel_selection(page,'fuel',[target['fuel']])
            panel.locator('#filterSearch').fill(target['station'])
            page.keyboard.press('Escape')
            # Escape inside a disclosure still cancels the complete draft.
            expect(panel).to_have_count(0)
            page.get_by_role('button',name='Filters',exact=True).click()
            if admin:panel_selection(page,'employee',[target['userId']])
            if view!='Overview':panel_selection(page,'status',[target['status']])
            if view=='Reports':panel_selection(page,'fuel',[target['fuel']])
            panel.locator('#filterSearch').fill(target['station'])
            panel.get_by_role('button',name='Apply Filters',exact=True).click()
            applied=page.evaluate('JSON.stringify(appliedFilterSnapshot())')
            assert page.evaluate('(view)=>view==="Overview"?recentSearch:view==="Reports"?reportSearch:search',view)==target['station']
            results=page.evaluate('(view)=>view==="Reports"?reportRows():view==="Receipts"?filteredReceipts():selected().filter(employeeMatch)',view)
            if admin:assert all(row['userId']==target['userId'] for row in results)
            if view!='Overview':assert all(row['status']==target['status'] and row['station']==target['station'] for row in results)
            assert results
            if admin and view!='Overview':
                label='Export filtered CSV' if view=='Reports' else 'Export CSV'
                with page.expect_download() as download:
                    page.get_by_role('button',name=label,exact=False).click()
                rows=list(csv.reader(io.StringIO(Path(download.value.path()).read_text())))
                assert 'Amount' in rows[0] and len(rows)==len(results)+1
            if view=='Reports':
                with page.expect_popup() as popup:
                    page.get_by_role('button',name='Export chart PDF',exact=False).click()
                popup.value.wait_for_load_state('domcontentloaded')
                expect(popup.value).to_have_title('UFB FuelTrack spending report')
                expect(popup.value.get_by_role('heading',name='Fuel spending',exact=False)).to_be_visible()
                expect(popup.value.locator('#spendingSVG')).to_have_count(1)
                popup.value.close()
            expect(page.locator('.mobile-filter-summary')).to_contain_text(target['station'])
            # Reset is a draft operation too, and documented defaults apply atomically.
            page.get_by_role('button',name='Filters',exact=True).click()
            panel.get_by_role('button',name='Reset',exact=True).click()
            assert page.evaluate('JSON.stringify(appliedFilterSnapshot())')==applied
            expect(panel.locator('#filterPeriod')).to_have_value('month')
            expect(panel.locator('#filterSearch')).to_have_value('')
            panel.get_by_role('button',name='Apply Filters',exact=True).click()
            assert page.evaluate('period')=='month'
            assert page.evaluate('(view)=>view==="Overview"?recentSearch:view==="Reports"?reportSearch:search',view)==''
            if admin:assert page.evaluate('multi.employee.length===0&&filterUser==="all"')
            if view!='Overview':assert page.evaluate('multi.status.length===0')
            if view=='Reports':assert page.evaluate('multi.fuel.length===0&&reportFuel==="all"')
            # Required primary ranges plus legacy capabilities remain selectable.
            page.get_by_role('button',name='Filters',exact=True).click()
            for preset in ['week','month','lastmonth','past3','all','today','yesterday','last7','last30','lastweek','quarter','lastquarter','year','lastyear']:
                panel.locator('#filterPeriod').select_option(preset)
                expected=page.evaluate('(key)=>datePresetBounds(key)',preset)
                expect(panel.locator('#filterFrom')).to_have_value(expected['from'])
                expect(panel.locator('#filterTo')).to_have_value(expected['to'])
            panel.locator('#filterPeriod').select_option('custom')
            panel.locator('#filterFrom').fill('')
            panel.get_by_role('button',name='Apply Filters',exact=True).click()
            expect(panel.locator('#filterRangeError')).to_contain_text('valid start date')
            panel.locator('#filterFrom').fill('2026-09-01');panel.locator('#filterTo').fill('2026-09-30')
            panel.get_by_role('button',name='Apply Filters',exact=True).click()
            assert page.evaluate('customFrom')=='2026-09-01'
            assert page.evaluate('customTo')=='2026-09-30'
            # An unchanged Apply preserves exact applied date/state semantics.
            snapshot=page.evaluate('JSON.stringify(appliedFilterSnapshot())')
            page.get_by_role('button',name='Filters',exact=True).click()
            panel.get_by_role('button',name='Apply Filters',exact=True).click()
            assert page.evaluate('JSON.stringify(appliedFilterSnapshot())')==snapshot
            assert_no_overflow(page)
        # Legacy single-status state must be reflected in the draft and can be cleared.
        page.evaluate("()=>{period='all';filterStatus='Pending';multi.status=[];tab='receipts';render()}")
        page.get_by_role('button',name='Filters',exact=True).click()
        panel=page.get_by_role('dialog',name='Filters',exact=True)
        expect(panel.locator('input[name="status"][value="Pending"]')).to_be_checked()
        assert panel.locator('input[name="status"]:checked').count()==1
        group=panel.locator('details[data-filter-type="status"]');group.locator('summary').click()
        group.get_by_role('button',name='Select all',exact=True).click()
        panel.get_by_role('button',name='Apply Filters',exact=True).click()
        assert page.evaluate('filterStatus')=='all'
        assert page.evaluate('multi.status.length')==0
        # Check common date math with known calendar boundaries, independently of the UI.
        bounds=page.evaluate("()=>Object.fromEntries(['week','month','lastmonth','past3','all'].map(key=>[key,datePresetBounds(key,new Date(2026,0,7,12))]))")
        assert bounds=={'week':{'from':'2026-01-05','to':'2026-01-07'},'month':{'from':'2026-01-01','to':'2026-01-07'},'lastmonth':{'from':'2025-12-01','to':'2025-12-31'},'past3':{'from':'2025-10-07','to':'2026-01-07'},'all':{'from':'2025-01-07','to':'2026-01-07'}}
        assert page.evaluate("datePresetBounds('past3',new Date(2026,4,31,12)).from")=='2026-02-28'
        page.get_by_role('button',name='Filters',exact=True).click()
        panel=page.get_by_role('dialog',name='Filters',exact=True)
        page.keyboard.press('Shift+Tab')
        expect(panel.get_by_role('button',name='Apply Filters',exact=True)).to_be_focused()
        page.set_viewport_size({'width':375,'height':420})
        expect(panel).to_be_visible()
        assert panel.bounding_box()['height']<=420
        page.set_viewport_size({'width':1024,'height':900})
        expect(panel).to_have_count(0)
        assert page.locator('body').evaluate('e=>e.style.position')!='fixed'
        expect(page.locator('.mobile-filter-launcher')).to_have_count(0)
        expect(page.locator('.range-trigger').first).to_be_visible()
        assert not errors,errors
        context.close()
    print('PASS: unified filter drafts, presets/custom validation, simultaneous filters/search, reset, cancellation, scroll/focus lock and viewport resizing')
