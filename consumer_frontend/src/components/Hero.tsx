const QUIZ_URL = 'https://form.typeform.com/to/sf98mAlp'

export default function Hero() {
  return (
    <section className="min-h-screen flex items-center justify-center bg-gradient-to-b from-primary-light/10 to-white">
      <div className="container-custom py-12 sm:py-16 md:py-20">
        <div className="text-center space-y-8 sm:space-y-10">
          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-display font-bold text-gray-900 leading-tight">
           Get real information
            <br />
            <span className="text-primary">based on your unique child</span>
          </h1>
          
          {/* Supporting Text */}
          <p className="text-lg sm:text-xl md:text-2xl text-gray-600 max-w-2xl mx-auto leading-relaxed">
            Start by answering a few questions to help us get a better understanding of your childs challenges. We'll put together a custom report that shares what has worked for parents with similar kids.
          </p>
          
          {/* Primary CTA */}
          <div className="pt-4 sm:pt-6">
            <a 
              href={QUIZ_URL}
              className="btn-primary"
              aria-label="Take the parent support quiz"
            >
              Get Started
            </a>
          </div>
          
          {/* Optional subtext */}
          <p className="text-sm sm:text-base text-gray-500 pt-4">
            This is a free report. We'll never share your data and we won't ask anything too personal
          </p>
        </div>
      </div>
    </section>
  )
}
