import { BrowserRouter, Routes, Route } from "react-router-dom"
import { UploadArea } from "./components/UploadArea"
import { PersonaViewer } from "./components/PersonaViewer"
import { PersonaSandbox } from "./components/PersonaSandbox"
import { CoachView } from "./components/CoachView"
import { TimelineView } from "./components/TimelineView"
import { CompareView } from "./components/CompareView"

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen dark">
        <Routes>
          <Route path="/" element={
            <div className="flex min-h-screen flex-col items-center justify-center p-24">
              <h1 className="text-5xl font-bold tracking-tight mb-4 bg-gradient-to-br from-white to-white/40 bg-clip-text text-transparent">PersonaForge</h1>
              <p className="text-xl text-white/50 mb-12">Turn conversations into living personas.</p>
              <UploadArea />
            </div>
          } />
          <Route path="/persona/:id" element={<PersonaViewer />} />
          <Route path="/sandbox/:id" element={<PersonaSandbox />} />
          <Route path="/coach/:id" element={<CoachView />} />
          <Route path="/timeline/:id" element={<TimelineView />} />
          <Route path="/compare/:id1/:id2" element={<CompareView />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
