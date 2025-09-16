'use client'

import { useState } from 'react'
import Link from 'next/link'

export default function Demo() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Hero Section */}
      <div className="pt-20 pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-6">
            See Hall of Fame LM in Action
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
        <div className="mb-12">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Choose Your AI Personality</h2>
            <p className="text-lg text-gray-600">See how the same recap changes with different styles</p>
          </div>
          
          <PersonalityShowcase />
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

function PersonalityShowcase() {
  const [selectedStyle, setSelectedStyle] = useState<string>('balanced')
  const [generatedText, setGeneratedText] = useState<string>('')
  const [isGenerating, setIsGenerating] = useState(false)

  const personalities = [
    {
      id: 'balanced',
      name: 'Balanced',
      icon: '⚖️',
      color: 'green',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      textColor: 'text-green-700',
      buttonColor: 'bg-green-600 hover:bg-green-700',
      example: '"Mike\'s team put up 142 points this week, led by strong performances from Lamar Jackson (28 pts) and Mark Andrews (19 pts). This consistent scoring has moved them to the top of our power rankings."',
      liveExamples: [
        "Sarah's waiver pickup of Puka Nacua proves her strategic planning is paying off.",
        "The league's top scorer this week showed excellent roster management.",
        "A well-balanced performance across all positions led to this decisive victory."
      ]
    },
    {
      id: 'hype',
      name: 'Hype',
      icon: '🔥',
      color: 'red',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      textColor: 'text-red-700',
      buttonColor: 'bg-red-600 hover:bg-red-700',
      example: '"LAMAR JACKSON IS ON FIRE! 🔥🔥 Mike\'s Dream Team just OBLITERATED the competition with 142 MASSIVE points! That Ravens stack is UNSTOPPABLE! WHO\'S GONNA STOP THIS FREIGHT TRAIN?! 🚂💨"',
      liveExamples: [
        "SARAH IS A WAIVER WIRE WIZARD! 🧙‍♀️ That Puka pickup was GENIUS!",
        "UNSTOPPABLE! UNBEATABLE! This team is CRUSHING the competition! 💪",
        "FIRE EMOJI FIRE EMOJI! This performance was ABSOLUTELY LEGENDARY! 🔥🔥🔥"
      ]
    },
    {
      id: 'nerd',
      name: 'Nerd',
      icon: '🤓',
      color: 'blue',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      textColor: 'text-blue-700',
      buttonColor: 'bg-blue-600 hover:bg-blue-700',
      example: '"Mike\'s 142.3 points represents a 23% increase from his season average (115.8). The Lamar-Andrews correlation coefficient of 0.73 continues to drive optimal lineup construction. Advanced metrics favor continued dominance."',
      liveExamples: [
        "Sarah's FAAB efficiency ratio of 2.3 points per dollar demonstrates superior resource allocation.",
        "This 18.7% above-projection performance indicates optimal weekly lineup optimization.",
        "The 0.89 correlation between waiver activity and season-end ranking validates this strategy."
      ]
    },
    {
      id: 'snark',
      name: 'Snark',
      icon: '😏',
      color: 'purple',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200',
      textColor: 'text-purple-700',
      buttonColor: 'bg-purple-600 hover:bg-purple-700',
      example: '"Oh look, Mike won again. Shocking. 🙄 I\'m sure it has nothing to do with autodrafting the Ravens stack while the rest of you were arguing about kicker strategy. But hey, at least you tried! 😏"',
      liveExamples: [
        "Sarah actually read the waiver wire articles. What a concept! 📚",
        "Wow, someone finally remembered to set their lineup. Gold star! ⭐",
        "Oh, you benched your best player again? Bold strategy, Cotton. 🤦‍♂️"
      ]
    }
  ]

  const generateLiveText = async () => {
    setIsGenerating(true)
    const personality = personalities.find(p => p.id === selectedStyle)
    
    // Simulate API call delay
    setTimeout(() => {
      if (personality) {
        const randomExample = personality.liveExamples[Math.floor(Math.random() * personality.liveExamples.length)]
        setGeneratedText(randomExample)
      }
      setIsGenerating(false)
    }, 1500)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {personalities.map((personality) => (
          <div
            key={personality.id}
            className={`bg-white rounded-xl shadow-lg overflow-hidden border-2 transition-all duration-200 cursor-pointer ${
              selectedStyle === personality.id 
                ? personality.borderColor + ' ring-2 ring-offset-2 ring-' + personality.color + '-500' 
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => setSelectedStyle(personality.id)}
          >
            <div className={`${personality.bgColor} px-6 py-4 border-b ${personality.borderColor}`}>
              <div className="flex items-center space-x-3">
                <span className="text-2xl">{personality.icon}</span>
                <div>
                  <h3 className={`text-lg font-semibold ${personality.textColor}`}>
                    {personality.name} Style
                  </h3>
                  <p className="text-sm text-gray-600">
                    {personality.id === 'balanced' && 'Professional and informative'}
                    {personality.id === 'hype' && 'High energy and excitement'}
                    {personality.id === 'nerd' && 'Data-driven and analytical'}
                    {personality.id === 'snark' && 'Witty and sarcastic'}
                  </p>
                </div>
                {selectedStyle === personality.id && (
                  <div className={`ml-auto w-6 h-6 rounded-full ${personality.buttonColor} flex items-center justify-center`}>
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </div>
            </div>
            
            <div className="p-6">
              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 leading-relaxed">
                {personality.example}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Interactive Generator */}
      <div className="bg-white rounded-xl shadow-lg p-8 text-center">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">
          Try {personalities.find(p => p.id === selectedStyle)?.name} Style Live
        </h3>
        
        <button
          onClick={generateLiveText}
          disabled={isGenerating}
          className={`inline-flex items-center justify-center px-6 py-3 text-white font-semibold rounded-lg transition-all duration-200 ${
            personalities.find(p => p.id === selectedStyle)?.buttonColor
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {isGenerating ? (
            <>
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Generating...
            </>
          ) : (
            <>
              Try it live
              <svg className="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </>
          )}
        </button>

        {generatedText && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg border-l-4 border-blue-500">
            <p className="text-gray-800 italic">"{generatedText}"</p>
            <p className="text-xs text-gray-500 mt-2">
              Generated with {personalities.find(p => p.id === selectedStyle)?.name} personality
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
