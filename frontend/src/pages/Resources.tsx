import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import ResourceForm from '../components/ResourceForm'
import ResourceList from '../components/ResourceList'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface Resource {
  id: number
  title: string
  category: string
  short_description: string
  long_description: string
  link: string
  thumbnail: string | null
  is_featured: boolean
  view_count: number
  link_status: string
  last_checked: string | null
  created_at: string
  updated_at: string
  tags: Array<{ id: number; name: string }>
}

export default function Resources() {
  const [resources, setResources] = useState<Resource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingResource, setEditingResource] = useState<Resource | null>(null)
  const [checkingLinks, setCheckingLinks] = useState(false)
  const { token } = useAuth()

  useEffect(() => {
    fetchResources()
  }, [token])

  const fetchResources = async () => {
    if (!token) return

    try {
      setLoading(true)
      setError(null)
      const response = await fetch(`${API_URL}/api/resources?page=1&page_size=100`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch resources: ${response.statusText}`)
      }

      const data = await response.json()
      setResources(data.resources || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load resources')
      console.error('Error fetching resources:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    setEditingResource(null)
    setShowForm(true)
  }

  const handleEdit = (resource: Resource) => {
    setEditingResource(resource)
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this resource?')) return

    try {
      const response = await fetch(`${API_URL}/api/resources/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error('Failed to delete resource')
      }

      await fetchResources()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete resource')
    }
  }

  const handleDuplicate = async (id: number) => {
    try {
      const response = await fetch(`${API_URL}/api/resources/${id}/duplicate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error('Failed to duplicate resource')
      }

      await fetchResources()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to duplicate resource')
    }
  }

  const handleCheckAllLinks = async () => {
    if (!confirm('This will check all resource links. Continue?')) return

    setCheckingLinks(true)
    try {
      const response = await fetch(`${API_URL}/api/resources/check-all-links`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error('Failed to check links')
      }

      const data = await response.json()
      alert(`Checked ${data.total_checked} links`)
      await fetchResources()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to check links')
    } finally {
      setCheckingLinks(false)
    }
  }

  const handleFormSuccess = async () => {
    setShowForm(false)
    setEditingResource(null)
    await fetchResources()
  }

  const handleFormCancel = () => {
    setShowForm(false)
    setEditingResource(null)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Resource Management</h1>
              <p className="mt-2 text-sm text-gray-600">
                Manage resources for the consumer frontend
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleCheckAllLinks}
                disabled={checkingLinks}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
              >
                {checkingLinks ? 'Checking...' : 'Check All Links'}
              </button>
              <button
                onClick={handleCreate}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                + Add Resource
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {showForm && (
          <ResourceForm
            resource={editingResource}
            onSuccess={handleFormSuccess}
            onCancel={handleFormCancel}
          />
        )}

        {!loading && !error && !showForm && (
          <ResourceList
            resources={resources}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onDuplicate={handleDuplicate}
          />
        )}
      </main>
    </div>
  )
}
