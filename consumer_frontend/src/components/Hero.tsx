const QUIZ_URL = 'https://form.typeform.com/to/sf98mAlp'

export default function Hero() {
  return (
    <section className="min-h-screen flex items-center justify-center bg-gradient-to-b from-primary-light/10 to-white">
      <div className="container-custom py-12 sm:py-16 md:py-20">
        <div className="text-center space-y-8 sm:space-y-10">
          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-display font-bold text-gray-900 leading-tight">
            Find Your Village,
            <br />
            <span className="text-primary">One Question at a Time</span>
          </h1>
          
          {/* Supporting Text */}
          <p className="text-lg sm:text-xl md:text-2xl text-gray-600 max-w-2xl mx-auto leading-relaxed">
            A quick quiz to connect you with other parents who get it. 
            Real support, real experiences, real community.
          </p>
          
          {/* Primary CTA */}
          <div className="pt-4 sm:pt-6">
            <a 
              href={QUIZ_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary"
              aria-label="Take the parent support quiz"
            >
              Take the Quiz
            </a>
          </div>
          
          {/* Optional subtext */}
          <p className="text-sm sm:text-base text-gray-500 pt-4">
            Takes about 3 minutes · No email required
          </p>
        </div>
      </div>
    </section>
  )
}
