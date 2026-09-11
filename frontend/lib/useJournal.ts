'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { emptyJournal, Journal, localDate, millisecondsToMidnight, STORAGE_KEY } from './meals'
import { browserJournalStorage, JournalStorage } from './journalStorage'

export function useJournal(storage: JournalStorage = browserJournalStorage) {
  const [journal, setJournal] = useState(emptyJournal)
  const [ready, setReady] = useState(false)
  const [storageError, setStorageError] = useState('')
  const blocked = useRef(false)
  const [today, setToday] = useState('')

  useEffect(() => {
    const read = () => {
      try {
        const loaded = storage.read()
        setJournal(loaded)
        blocked.current = false
        setStorageError('')
      } catch (error) {
        blocked.current = true
        setStorageError(`${error instanceof Error ? error.message : 'Browser storage is unavailable.'} Saving is paused; scanning still works. Existing data will not be overwritten.`)
      }
      setReady(true)
    }
    read()
    const onStorage = (event: StorageEvent) => { if (event.key === STORAGE_KEY || event.key === null) read() }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [storage])

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>
    const refresh = () => {
      clearTimeout(timer)
      setToday(localDate())
      timer = setTimeout(refresh, millisecondsToMidnight() + 50)
    }
    refresh()
    window.addEventListener('focus', refresh)
    document.addEventListener('visibilitychange', refresh)
    return () => { clearTimeout(timer); window.removeEventListener('focus', refresh); document.removeEventListener('visibilitychange', refresh) }
  }, [])

  const commit = useCallback((change: (previous: Journal) => Journal): boolean => {
    if (!ready || blocked.current) return false
    try {
      // Read again so another tab's most recent saved meals are not discarded.
      const stored = storage.read()
      const next = storage.write(change(stored))
      setJournal(next)
      setStorageError('')
      return true
    } catch (error) {
      setStorageError(`Changes could not be saved in this browser. ${error instanceof Error ? error.message : 'Storage is unavailable.'} Your previous saved meals are unchanged; scanning still works.`)
      return false
    }
  }, [ready, storage])

  return { journal, commit, ready, today, storageError }
}
