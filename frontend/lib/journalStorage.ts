import { Journal, parseJournal, STORAGE_KEY } from './meals'

export interface JournalStorage {
  read(): Journal
  write(journal: Journal): Journal
}

// Storage access is lazy: SSR and blocked localStorage never prevent app startup.
export const browserJournalStorage: JournalStorage = {
  read: () => parseJournal(window.localStorage.getItem(STORAGE_KEY)),
  write: journal => {
    const validated = parseJournal(JSON.stringify(journal))
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(validated))
    return validated
  },
}
