import Link from 'next/link'

export default function Demo() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Hero Section */}
      <div className="pt-20 pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-6">
            See All Pro Commish in Action
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-12">
            Experience how our AI transforms boring league management into engaging, 
            entertaining content that keeps your league talking all season long.
          </p>
        </div>
      </div>

      {/* Demo Content */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        {/* Power Rankings Demo */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-12">
          <div className="flex items-center mb-6">
            <div className="bg-yellow-100 w-12 h-12 rounded-full flex items-center justify-center mr-4">
              <span className="text-2xl">🏆</span>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Weekly Power Rankings</h2>
              <p className="text-gray-600">Tuesday, Week 8 • Generated in 30 seconds</p>
            </div>
          </div>
          
          <div className="bg-gray-50 rounded-lg p-6 space-y-4">
            <div className="border-l-4 border-green-500 pl-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-gray-900">#1 The Dream Team (7-1)</h3>
                <span className="text-green-600 font-medium">↑ 2</span>
              </div>
              <p className="text-gray-600 mt-1">
                <strong>Mike's squad</strong> continues their scorching hot streak with another dominant performance. 
                That Lamar-Andrews stack is looking unstoppable, and frankly, the rest of us are just playing for second place at this point. 🔥
              </p>
            </div>
            
            <div className="border-l-4 border-blue-500 pl-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-gray-900">#2 Waiver Wire Warriors (6-2)</h3>
                <span className="text-blue-600 font-medium">→ 0</span>
              </div>
              <p className="text-gray-600 mt-1">
                <strong>Sarah</strong> proving that you don't need to draft well when you can pick up every breakout player 
                before anyone else notices. That $47 FAAB bid on Puka Nacua in Week 2 is looking genius now. 🧠
              </p>
            </div>
            
            <div className="border-l-4 border-orange-500 pl-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-gray-900">#3 Injured Reserve FC (5-3)</h3>
                <span className="text-orange-600 font-medium">↓ 1</span>
              </div>
              <p className="text-gray-600 mt-1">
                <strong>Jake's</strong> team has more injury reports than a MASH unit, but somehow keeps winning. 
                When your RB1 is a practice squad guy and you're still competitive, that's just pure luck. 🍀
              </p>
            </div>
          </div>
          
          <div className="mt-6 flex items-center justify-between text-sm text-gray-500">
            <span>Generated with "Snark" personality • 2.3k characters</span>
            <span>📱 Auto-posted to GroupMe</span>
          </div>
        </div>

        {/* Waiver Report Demo */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-12">
          <div className="flex items-center mb-6">
            <div className="bg-green-100 w-12 h-12 rounded-full flex items-center justify-center mr-4">
              <span className="text-2xl">💰</span>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Waiver Wire Recap</h2>
              <p className="text-gray-600">Wednesday, Week 8 • FAAB Bloodbath Edition</p>
            </div>
          </div>
          
          <div className="bg-gray-50 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">This Week's Waiver Carnage:</h3>
            
            <div className="space-y-3">
              <div className="bg-white rounded-lg p-4 border-l-4 border-red-500">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-gray-900">
                      <strong>Sarah</strong> swoops in with <span className="text-red-600 font-bold">$89 FAAB</span> for Kyren Williams
                    </p>
                    <p className="text-gray-600 text-sm mt-1">Next highest bid: $23 (Mike). Ouch. 😬</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg p-4 border-l-4 border-orange-500">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-gray-900">
                      <strong>Jake</strong> panic-drops Christian McCaffrey for <strong>Dare Ogunbowale</strong>
                    </p>
                    <p className="text-gray-600 text-sm mt-1">Injury concerns or complete mental breakdown? You decide. 🤔</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg p-4 border-l-4 border-blue-500">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-gray-900">
                      <strong>Chris</strong> adds DeAndre Hopkins ($34) while already rostering 8 WRs
                    </p>
                    <p className="text-gray-600 text-sm mt-1">Starting to think you're collecting them like Pokemon cards. 🃏</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="mt-6 pt-4 border-t border-gray-200">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Total FAAB spent this week:</span>
                <span className="font-bold text-gray-900">$247 of $1,200 remaining</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div className="bg-blue-600 h-2 rounded-full" style={{width: '20.6%'}}></div>
              </div>
            </div>
          </div>
        </div>

        {/* Personality Showcase */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">📊 Balanced Style</h3>
            <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700">
              "Mike's team put up 142 points this week, led by strong performances from Lamar Jackson (28 pts) 
              and Mark Andrews (19 pts). This consistent scoring has moved them to the top of our power rankings."
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🔥 Hype Style</h3>
            <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700">
              "LAMAR JACKSON IS ON FIRE! 🔥🔥 Mike's Dream Team just OBLITERATED the competition with 142 MASSIVE points! 
              That Ravens stack is UNSTOPPABLE! WHO'S GONNA STOP THIS FREIGHT TRAIN?! 🚂💨"
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🤓 Nerd Style</h3>
            <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700">
              "Mike's 142.3 points represents a 23% increase from his season average (115.8). The Lamar-Andrews correlation 
              coefficient of 0.73 continues to drive optimal lineup construction. Advanced metrics favor continued dominance."
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">😈 Snark Style</h3>
            <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700">
              "Oh look, Mike won again. Shocking. 🙄 I'm sure it has nothing to do with autodrafting the Ravens stack 
              while the rest of you were arguing about kicker strategy. But hey, at least you tried! 😏"
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="bg-blue-600 rounded-xl p-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to automate your league?</h2>
          <p className="text-xl text-blue-100 mb-8">
            Stop spending hours writing content. Let AI handle it in seconds.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link 
              href="/auth/signup"
              className="inline-flex items-center justify-center px-8 py-4 text-lg font-semibold rounded-full text-blue-600 bg-white hover:bg-gray-50 transform hover:scale-105 transition-all duration-200"
            >
              Start Free Trial
            </Link>
            <Link 
              href="/connect"
              className="inline-flex items-center justify-center px-8 py-4 text-lg font-semibold rounded-full text-white border-2 border-white hover:bg-white hover:text-blue-600 transition-all duration-200"
            >
              Connect Your League
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
