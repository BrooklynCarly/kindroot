import { useState } from 'react'
import { Resource } from '../pages/Resources'
import { useAuth } from '../contexts/AuthContext'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface ResourceListProps {
  resources: Resource[]
  onEdit: (resource: Resource) => void
  onDelete: (id: number) => void
  onDuplicate: (id: number) => void
}

export default function ResourceList({ resources, onEdit, onDelete, onDuplicate }: ResourceListProps) {
  const { token } = useAuth()
  const [checkingLink, setCheckingLink] = useState<number | null>(null)
  const [filter, setFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')

  const handleCheckLink = async (resourceId: number) => {
    setCheckingLink(resourceId)
    try {
      const response = await fetch(`${API_URL}/api/resources/${resourceId}/check-link`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error('Failed to check link')
      }

      const data = await response.json()
      alert(`Link status: ${data.status}`)
      window.location.reload()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to check link')
    } finally {
      setCheckingLink(null)
    }
  }

  const categories = Array.from(new Set(resources.map(r => r.category))).sort()

  const filteredResources = resources.filter(resource => {
    const matchesSearch = filter === '' || 
      resource.title.toLowerCase().includes(filter.toLowerCase()) ||
      resource.short_description.toLowerCase().includes(filter.toLowerCase())
    
    const matchesCategory = categoryFilter === '' || resource.category === categoryFilter

    return matchesSearch && matchesCategory
  })

  return (
    <div>
      <div className="mb-6 flex gap-4">
        <input
          type="text"
          placeholder="Search resources..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Categories</option>
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Resource
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Category
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tags
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Views
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredResources.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                    No resources found
                  </td>
                </tr>
              ) : (
                filteredResources.map((resource) => (
                  <tr key={resource.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex items-start gap-3">
                        {resource.thumbnail && (
                          <img
                            src={resource.thumbnail}
                            alt=""
                            className="w-12 h-12 object-cover rounded"
                          />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {resource.title}
                            </p>
                            {resource.is_featured && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                                Featured
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-500 line-clamp-2">
                            {resource.short_description}
                          </p>
                          <a
                            href={resource.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-blue-600 hover:underline truncate block"
                          >
                            {resource.link}
                          </a>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-900">{resource.category}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {resource.tags.slice(0, 3).map(tag => (
                          <span
                            key={tag.id}
                            className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                          >
                            {tag.name}
                          </span>
                        ))}
                        {resource.tags.length > 3 && (
                          <span className="text-xs text-gray-500">
                            +{resource.tags.length - 3}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            resource.link_status === 'working'
                              ? 'bg-green-100 text-green-800'
                              : resource.link_status === 'broken'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {resource.link_status}
                        </span>
                        <button
                          onClick={() => handleCheckLink(resource.id)}
                          disabled={checkingLink === resource.id}
                          className="text-xs text-blue-600 hover:underline disabled:opacity-50"
                        >
                          {checkingLink === resource.id ? 'Checking...' : 'Check'}
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {resource.view_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => onEdit(resource)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => onDuplicate(resource.id)}
                          className="text-green-600 hover:text-green-900"
                        >
                          Duplicate
                        </button>
                        <button
                          onClick={() => onDelete(resource.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-4 text-sm text-gray-600">
        Showing {filteredResources.length} of {resources.length} resources
      </div>
    </div>
  )
}
