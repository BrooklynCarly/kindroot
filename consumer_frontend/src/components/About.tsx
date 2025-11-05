const QUIZ_URL = 'https://form.typeform.com/to/sf98mAlp'

export default function About() {
  return (
    <section className="py-16 sm:py-20 md:py-24 bg-white">
      <div className="container-custom">
        <div className="max-w-3xl mx-auto space-y-8">
          {/* Heading */}
          <h2 className="text-3xl sm:text-4xl font-display font-bold text-gray-900 text-center">
            Why We Made This
          </h2>
          
          {/* Personal Story */}
          <div className="prose prose-lg max-w-none space-y-6 text-gray-700">
            <p className="text-lg leading-relaxed">
              We're parents, just like you. And we know how isolating it can feel when you're 
              navigating the ups and downs of raising kids—especially when you're not sure where 
              to turn for advice that actually feels real.
            </p>
            
            <p className="text-lg leading-relaxed">
              This quiz isn't about selling you anything or telling you what to do. It's about 
              helping you find other parents who are going through similar experiences. Because 
              sometimes, the best support comes from someone who's been there too.
            </p>
            
            <p className="text-lg leading-relaxed">
              We built this as a simple way to connect parents with each other—no algorithms, 
              no ads, just real people sharing real stories. Take the quiz, see what resonates, 
              and know that you're not alone in this.
            </p>
          </div>
          
          {/* Secondary CTA */}
          <div className="pt-8 text-center">
            <a 
              href={QUIZ_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary"
              aria-label="Take the parent support quiz"
            >
              Start the Quiz
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
