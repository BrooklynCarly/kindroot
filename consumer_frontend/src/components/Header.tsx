const QUIZ_URL = 'https://form.typeform.com/to/sf98mAlp'

export default function Header() {
  return (
    <a 
      href={QUIZ_URL}
      className="fixed top-0 left-0 right-0 z-50 bg-primary hover:bg-primary-dark transition-colors duration-200 shadow-md cursor-pointer block"
      aria-label="Take the parent support quiz"
    >
      <div className="container-custom">
        <div className="flex items-center justify-center h-14 sm:h-16">
          <span className="text-base sm:text-lg font-semibold text-white">
            Take the quiz
          </span>
        </div>
      </div>
    </a>
  )
}
