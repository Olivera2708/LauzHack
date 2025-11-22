import './App.css'
import { Route, Routes} from "react-router-dom";
import CodePreview from "./components/codePreview.tsx";
import Home from "./components/home.tsx";


function App() {

  return (
      <Routes>
          <Route path="/" element={<CodePreview />} />
          <Route path="/home" element={<Home />} />
      </Routes>
  )
}

export default App
