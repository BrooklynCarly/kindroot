import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import Header from '../components/Header'

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
  long_description: string
  link: string
  thumbnail: string | null
  tags: Tag[]
  view_count: number
}

export default function ResourceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [resource, setResource] = useState<Resource | null>(null)
  const [relatedResources, setRelatedResources] = useState<Resource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (id) {
      fetchResource()
      fetchRelatedResources()
    }
  }, [id])

  const fetchResource = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch(`${API_URL}/api/resources/${id}`)
      
      if (!response.ok) {
        throw new Error('Resource not found')
      }
      
      const data = await response.json()
      setResource(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load resource')
    } finally {
      setLoading(false)
    }
  }

  const fetchRelatedResources = async () => {
    try {
      const response = await fetch(`${API_URL}/api/resources/${id}/related?limit=4`)
      
      if (response.ok) {
        const data = await response.json()
        setRelatedResources(data)
      }
    } catch (error) {
      console.error('Failed to fetch related resources:', error)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-white">
        <Header />
        <div className="pt-14 sm:pt-16 flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </div>
    )
  }

  if (error || !resource) {
    return (
      <div className="min-h-screen bg-white">
        <Header />
        <div className="pt-14 sm:pt-16 container-custom py-12">
          <div className="text-center">
            <p className="text-red-600 text-lg mb-4">{error || 'Resource not found'}</p>
            <Link to="/resources" className="text-primary hover:underline">
              ← Back to Resources
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white">
      <Header />
      
      <main className="pt-14 sm:pt-16">
        {/* Breadcrumb */}
        <nav className="bg-gray-50 border-b border-gray-200 py-4">
          <div className="container-custom">
            <ol className="flex items-center space-x-2 text-sm">
              <li>
                <Link to="/" className="text-primary hover:underline">
                  Home
                </Link>
              </li>
              <li className="text-gray-400">/</li>
              <li>
                <Link to="/resources" className="text-primary hover:underline">
                  Resources
                </Link>
              </li>
              <li className="text-gray-400">/</li>
              <li className="text-gray-600 truncate max-w-xs">{resource.title}</li>
            </ol>
          </div>
        </nav>

        {/* Resource Content */}
        <section className="py-12 sm:py-16">
          <div className="container-custom max-w-4xl">
            {/* Back Link */}
            <Link 
              to="/resources" 
              className="inline-flex items-center text-primary hover:underline mb-6"
            >
              ← Back to Resources
            </Link>

            {/* Thumbnail */}
            {resource.thumbnail && (
              <img
                src={resource.thumbnail}
                alt={resource.title}
                className="w-full h-64 sm:h-96 object-cover rounded-lg mb-8"
              />
            )}

            {/* Title & Category */}
            <div className="mb-6">
              <div className="flex items-center gap-3 mb-4">
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-primary/10 text-primary">
                  {resource.category}
                </span>
                <span className="text-sm text-gray-500">
                  {resource.view_count} views
                </span>
              </div>
              <h1 className="text-3xl sm:text-4xl font-display font-bold text-gray-900 mb-4">
                {resource.title}
              </h1>
              <p className="text-lg sm:text-xl text-gray-600">
                {resource.short_description}
              </p>
            </div>

            {/* Tags */}
            {resource.tags.length > 0 && (
              <div className="mb-8">
                <div className="flex flex-wrap gap-2">
                  {resource.tags.map((tag) => (
                    <span
                      key={tag.id}
                      className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-700"
                    >
                      {tag.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Long Description */}
            <div className="prose prose-lg max-w-none mb-8">
              <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">
                {resource.long_description}
              </div>
            </div>

            {/* Visit Resource Button */}
            <div className="mb-12">
              <a
                href={resource.link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block px-8 py-4 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors font-semibold text-lg shadow-md hover:shadow-lg"
              >
                Visit Resource →
              </a>
            </div>

            {/* Divider */}
            <hr className="border-gray-200 my-12" />

            {/* Related Resources */}
            {relatedResources.length > 0 && (
              <div>
                <h2 className="text-2xl sm:text-3xl font-display font-bold text-gray-900 mb-6">
                  Related Resources
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {relatedResources.map((related) => (
                    <Link
                      key={related.id}
                      to={`/resources/${related.id}`}
                      className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
                      onClick={() => window.scrollTo(0, 0)}
                    >
                      {related.thumbnail && (
                        <img
                          src={related.thumbnail}
                          alt={related.title}
                          className="w-full h-40 object-cover"
                        />
                      )}
                      <div className="p-4">
                        <h3 className="text-lg font-display font-bold text-gray-900 mb-2">
                          {related.title}
                        </h3>
                        <p className="text-sm text-primary font-medium mb-2">
                          {related.category}
                        </p>
                        <p className="text-gray-600 text-sm line-clamp-2">
                          {related.short_description}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
