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
              We're parents, just like you. We built this to help us sift through the noise and find information to help us set our kids up for success.
            </p>
            
            <p className="text-lg leading-relaxed">
              The questions in the form allow us to build a report with tailored information to your child (based on similar children). We are not trying to sell you anything and we'll never share your data - we don't even ask their name!
            </p>
            
            {/* <p className="text-lg leading-relaxed">
              We built this as a simple way to connect parents with each other—no algorithms, 
              no ads, just real people sharing real stories. Take the quiz, see what resonates, 
              and know that you're not alone in this.
            </p> */}
          </div>
          
          {/* Secondary CTA */}
          <div className="pt-8 text-center">
            <a 
              href={QUIZ_URL}
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
