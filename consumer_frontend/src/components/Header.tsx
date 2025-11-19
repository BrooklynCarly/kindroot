import { Link } from 'react-router-dom'

const QUIZ_URL = 'https://form.typeform.com/to/sf98mAlp'

export default function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-primary shadow-md">
      <div className="container-custom">
        <div className="flex items-center justify-between h-14 sm:h-16">
          <Link 
            to="/"
            className="text-base sm:text-lg font-semibold text-white hover:text-white/90 transition-colors"
          >
            KindRoot
          </Link>
          
          <nav className="flex items-center gap-4 sm:gap-6">
            <Link
              to="/resources"
              className="text-sm sm:text-base font-medium text-white hover:text-white/90 transition-colors"
            >
              Resources
            </Link>
            <a
              href={QUIZ_URL}
              className="px-4 py-2 bg-white text-primary rounded-lg hover:bg-gray-100 transition-colors font-semibold text-sm sm:text-base"
            >
              Take the Quiz
            </a>
          </nav>
        </div>
      </div>
    </header>
  )
}
