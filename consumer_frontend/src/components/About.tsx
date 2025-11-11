export default function About() {
  return (
    <section className="py-16 sm:py-20 md:py-24 bg-white">
      <div className="container-custom">
        <div className="max-w-3xl mx-auto space-y-8">
          
          {/* About Content - No Container */}
          <div className="text-center space-y-6">
            <h2 className="text-3xl sm:text-4xl font-display font-bold text-gray-900">
              About
            </h2>
            <div className="space-y-4 text-gray-700">
              <p className="text-base sm:text-lg leading-relaxed">
                We're parents, just like you. We built this to help us sift through the noise and find information to help us set our kids up for success.
              </p>
              <p className="text-base sm:text-lg leading-relaxed">
                The questions in the form allow us to build a report with tailored information to your child (based on similar children). We are not trying to sell you anything and we'll never share your data - we don't even ask their name!
              </p>
            </div>
          </div>
          
        </div>
      </div>
    </section>
  )
}
