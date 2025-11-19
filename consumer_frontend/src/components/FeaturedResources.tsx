import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface Tag {
  id: number
  name: string
}

interface Resource {
  id: number
  title: string
  category: string
  short_description: string
  thumbnail: string | null
  tags: Tag[]
}

export default function FeaturedResources() {
  const [resources, setResources] = useState<Resource[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchFeaturedResources()
  }, [])

  const fetchFeaturedResources = async () => {
    try {
      const response = await fetch(`${API_URL}/api/resources?featured_only=true&page_size=3`)
      
      if (response.ok) {
        const data = await response.json()
        setResources(data.resources || [])
      }
    } catch (error) {
      console.error('Failed to fetch featured resources:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading || resources.length === 0) {
    return null
  }

  return (
    <section className="py-12 sm:py-16 bg-gray-50">
      <div className="container-custom">
        <div className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl font-display font-bold text-gray-900 mb-4">
            Helpful Resources
          </h2>
          <p className="text-lg text-gray-600">
            Curated resources to support your journey
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-8">
          {resources.map((resource) => (
            <Link
              key={resource.id}
              to={`/resources/${resource.id}`}
              className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
            >
              {resource.thumbnail && (
                <img
                  src={resource.thumbnail}
                  alt={resource.title}
                  className="w-full h-48 object-cover"
                />
              )}
              <div className="p-6">
                <h3 className="text-xl font-display font-bold text-gray-900 mb-2">
                  {resource.title}
                </h3>
                <p className="text-sm text-primary font-medium mb-3">
                  {resource.category}
                </p>
                <p className="text-gray-600 text-sm line-clamp-3">
                  {resource.short_description}
                </p>
              </div>
            </Link>
          ))}
        </div>

        <div className="text-center">
          <Link
            to="/resources"
            className="inline-block px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors font-semibold"
          >
            View All Resources
          </Link>
        </div>
      </div>
    </section>
  )
}
