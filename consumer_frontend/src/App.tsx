import Header from './components/Header'
import Hero from './components/Hero'
import About from './components/About'

function App() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      <div className="pt-14 sm:pt-16">
        <Hero />
        <About />
      </div>
    </div>
  )
}

export default App
