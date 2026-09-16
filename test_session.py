import flet as ft
import asyncio

async def test_session():
    # Create a page manually
    page = ft.Page(ft.AppView.FULLscreen)
    page.title = "Test"
    
    # Try different session APIs
    print("Testing session APIs...")
    
    # Method 1: .set()
    try:
        page.session.set('test', 'value')
        print("  .set() worked")
    except Exception as e:
        print(f"  .set() error: {type(e).__name__}: {e}")
    
    # Method 2: .get()
    try:
        val = page.session.get('test')
        print(f"  .get() worked: {val}")
    except Exception as e:
        print(f"  .get() error: {type(e).__name__}: {e}")
    
    # Method 3: Check if session is a dict-like
    try:
        if isinstance(page.session, dict):
            print("  session is dict-like")
            page.session['test2'] = 'value2'
            print(f"  session['test2'] = {page.session.get('test2')}")
    except Exception as e:
        print(f"  session dict error: {type(e).__name__}: {e}")
    
    # Method 4: page.client_storage
    try:
        page.client_storage.set('test_cs', 'value_cs')
        val_cs = page.client_storage.get('test_cs')
        print(f"  client_storage.set/get worked: {val_cs}")
    except Exception as e:
        print(f"  client_storage error: {type(e).__name__}: {e}")

if __name__ == '__main__':
    ft.app(target=test_session)