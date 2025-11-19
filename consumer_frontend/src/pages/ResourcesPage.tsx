import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
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
  link: string
  thumbnail: string | null
  tags: Tag[]
  is_featured: boolean
}

export default function ResourcesPage() {
  const [resources, setResources] = useState<Resource[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [categories, setCategories] = useState<string[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 12

  useEffect(() => {
    fetchCategories()
  }, [])

  useEffect(() => {
    fetchResources()
  }, [page, selectedCategory, searchQuery])

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/api/resources/categories/list`)
      if (response.ok) {
        const data = await response.json()
        setCategories(data)
      }
    } catch (error) {
      console.error('Failed to fetch categories:', error)
    }
  }

  const fetchResources = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString()
      })
      
      if (selectedCategory) {
        params.append('category', selectedCategory)
      }
      
      if (searchQuery) {
        params.append('search', searchQuery)
      }

      const response = await fetch(`${API_URL}/api/resources?${params}`)
      
      if (response.ok) {
        const data = await response.json()
        setResources(data.resources || [])
        setTotal(data.total || 0)
      }
    } catch (error) {
      console.error('Failed to fetch resources:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1) // Reset to first page on new search
  }

  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category)
    setPage(1) // Reset to first page on category change
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="min-h-screen bg-white">
      <Header />
      
      <main className="pt-14 sm:pt-16">
        {/* Hero Section with Search */}
        <section className="bg-gradient-to-b from-primary-light/10 to-white py-12 sm:py-16">
          <div className="container-custom">
            <div className="text-center space-y-6">
              <h1 className="text-4xl sm:text-5xl font-display font-bold text-gray-900">
                Resources for Parents
              </h1>
              <p className="text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto">
                Helpful resources, support groups, and information curated for families
              </p>
              
              {/* Search Bar */}
              <form onSubmit={handleSearch} className="max-w-2xl mx-auto mt-8">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search resources..."
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent text-base"
                  />
                  <button
                    type="submit"
                    className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors font-semibold"
                  >
                    Search
                  </button>
                </div>
              </form>
            </div>
          </div>
        </section>

        {/* Category Filters */}
        <section className="py-6 border-b border-gray-200 bg-gray-50">
          <div className="container-custom">
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleCategoryChange('')}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  selectedCategory === ''
                    ? 'bg-primary text-white'
                    : 'bg-white text-gray-700 border border-gray-300 hover:border-primary'
                }`}
              >
                All
              </button>
              {categories.map((category) => (
                <button
                  key={category}
                  onClick={() => handleCategoryChange(category)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                    selectedCategory === category
                      ? 'bg-primary text-white'
                      : 'bg-white text-gray-700 border border-gray-300 hover:border-primary'
                  }`}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Resources Grid */}
        <section className="py-12 sm:py-16">
          <div className="container-custom">
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
              </div>
            ) : resources.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-600 text-lg">No resources found. Try adjusting your filters.</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
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
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <h3 className="text-xl font-display font-bold text-gray-900 flex-1">
                            {resource.title}
                          </h3>
                          {resource.is_featured && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-accent/20 text-accent-dark flex-shrink-0">
                              Featured
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-primary font-medium mb-3">
                          {resource.category}
                        </p>
                        <p className="text-gray-600 mb-4 line-clamp-3">
                          {resource.short_description}
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {resource.tags.slice(0, 3).map((tag) => (
                            <span
                              key={tag.id}
                              className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700"
                            >
                              {tag.name}
                            </span>
                          ))}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex justify-center gap-2">
                    <button
                      onClick={() => setPage(Math.max(1, page - 1))}
                      disabled={page === 1}
                      className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <span className="px-4 py-2 text-gray-700">
                      Page {page} of {totalPages}
                    </span>
                    <button
                      onClick={() => setPage(Math.min(totalPages, page + 1))}
                      disabled={page === totalPages}
                      className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
