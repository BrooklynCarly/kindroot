export default function Hero() {
  return (
    <section className="flex items-center justify-center bg-gradient-to-b from-primary-light/10 to-white">
      <div className="container-custom py-12 sm:py-16 md:py-20">
        <div className="space-y-10 sm:space-y-12 md:space-y-16">
          
          {/* Headline - Not in container */}
          <div className="text-center space-y-6">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-display font-bold text-gray-900 leading-tight">
              Get real information
              <br />
              <span className="text-primary">tailored for your kid</span>
            </h1>     
          </div>     
          {/* Who this is for & What this is - Side by Side on Desktop */}
          <div className="max-w-5xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
              
              {/* Who this is for Section */}
              <div className="bg-white rounded-lg p-6 sm:p-8 space-y-4 shadow-sm">
                <h2 className="text-2xl sm:text-3xl font-display font-bold text-gray-900">
                  Who this is for
                </h2>
                <ul className="space-y-3 text-gray-700">
                  <li className="flex items-start">
                    <span className="text-primary mr-3 flex-shrink-0">•</span>
                    <span className="text-base sm:text-lg leading-relaxed">Parents with tricky kids</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-primary mr-3 flex-shrink-0">•</span>
                    <span className="text-base sm:text-lg leading-relaxed">Parents who have concerns about Autism</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-primary mr-3 flex-shrink-0">•</span>
                    <span className="text-base sm:text-lg leading-relaxed">Parents whose kid was recently diagnosed with Autism</span>
                  </li>
                </ul>
              </div>

              {/* What this is Section */}
              <div className="bg-white rounded-lg p-6 sm:p-8 space-y-4 shadow-sm">
                <h2 className="text-2xl sm:text-3xl font-display font-bold text-gray-900">
                  What this is
                </h2>
                <ul className="space-y-3 text-gray-700">
                  <li className="flex items-start">
                    <span className="text-primary mr-3 flex-shrink-0">•</span>
                    <span className="text-base sm:text-lg leading-relaxed">A free Google Doc report</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-primary mr-3 flex-shrink-0">•</span>
                    <span className="text-base sm:text-lg leading-relaxed">Information to discuss with your pediatrician, related to your kid</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-primary mr-3 flex-shrink-0">•</span>
                    <span className="text-base sm:text-lg leading-relaxed">Local resources</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-primary mr-3 flex-shrink-0">•</span>
                    <span className="text-base sm:text-lg leading-relaxed">Strategies other similar families have tried</span>
                  </li>
                </ul>
              </div>
              
            </div>
          </div>
          
        </div>
      </div>
    </section>
  )
}
