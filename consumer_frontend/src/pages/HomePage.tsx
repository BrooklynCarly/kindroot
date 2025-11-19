import Header from '../components/Header'
import Hero from '../components/Hero'
import About from '../components/About'
import FeaturedResources from '../components/FeaturedResources'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      <div className="pt-14 sm:pt-16">
        <Hero />
        <FeaturedResources />
        <About />
      </div>
    </div>
  )
}
