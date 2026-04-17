import React from 'react'
import { AppProvider } from './context/AppContext'
import Sidebar from './components/layout/Sidebar'
import TopBar from './components/layout/TopBar'
import Dashboard from './pages/Dashboard'

export default function App() {
  return (
    <AppProvider>
      <div className="flex h-screen overflow-hidden font-body bg-earth-50">
        <Sidebar />
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <TopBar />
          <main className="flex-1 overflow-hidden">
            <Dashboard />
          </main>
        </div>
      </div>
    </AppProvider>
  )
}
