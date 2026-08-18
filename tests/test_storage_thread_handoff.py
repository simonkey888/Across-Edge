import sqlite3,threading
from across_edge.storage import Store


def test_store_connection_cannot_be_handed_across_threads(tmp_path):
    store=Store(tmp_path/'handoff.sqlite');result={}
    def worker():
        try:store.bump_counter('run-thread','cycles')
        except Exception as exc:result['error']=exc
    thread=threading.Thread(target=worker);thread.start();thread.join(timeout=5)
    assert not thread.is_alive()
    assert isinstance(result.get('error'),sqlite3.ProgrammingError)
    store.close()


def test_store_created_inside_worker_is_safe_and_closes(tmp_path):
    path=tmp_path/'owned.sqlite';result={}
    def worker():
        store=Store(path)
        try:store.bump_counter('run-thread','cycles');result['value']=store.counters('run-thread')['cycles']
        finally:store.close()
    thread=threading.Thread(target=worker);thread.start();thread.join(timeout=5)
    assert not thread.is_alive() and result['value']==1
