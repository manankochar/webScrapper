import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Video, FileText, BarChart3, Zap, Sparkles } from 'lucide-react';
import ScraperInterface from './components/ScraperInterface';
import VideoManager from './components/VideoManager';
import PDFManager from './components/PDFManager';
import ReportsManager from './components/ReportsManager';

type TabType = 'scraper' | 'videos' | 'pdfs' | 'reports';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('scraper');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  const tabs = [
    { id: 'scraper' as TabType, label: 'Quantum Scraper', icon: Zap, color: 'from-cyan-400 to-blue-500' },
    { id: 'videos' as TabType, label: 'Neural Videos', icon: Video, color: 'from-purple-400 to-pink-500' },
    { id: 'pdfs' as TabType, label: 'Holographic PDFs', icon: FileText, color: 'from-emerald-400 to-cyan-500' },
    { id: 'reports' as TabType, label: 'Data Analytics', icon: BarChart3, color: 'from-orange-400 to-red-500' },
  ];

  useEffect(() => {
    // Simulate loading animation
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  const handleScrapeStart = () => {
    // Trigger refresh of other tabs after a delay
    setTimeout(() => {
      setRefreshTrigger(prev => prev + 1);
    }, 2000);
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'scraper':
        return <ScraperInterface onScrapeStart={handleScrapeStart} />;
      case 'videos':
        return <VideoManager key={refreshTrigger} />;
      case 'pdfs':
        return <PDFManager key={refreshTrigger} />;
      case 'reports':
        return <ReportsManager />;
      default:
        return <ScraperInterface onScrapeStart={handleScrapeStart} />;
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen animated-bg flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8 }}
          className="text-center"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="w-20 h-20 mx-auto mb-8"
          >
            <Sparkles className="w-full h-full text-cyan-400" />
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.8 }}
            className="text-4xl font-bold holographic mb-4"
          >
            QUANTUM SCRAPER
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1, duration: 0.8 }}
            className="text-gray-300 text-lg"
          >
            Initializing Neural Networks...
          </motion.p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen animated-bg relative overflow-hidden">
      {/* Animated Background Particles */}
      <div className="particle-container">
        {[...Array(50)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-cyan-400 rounded-full"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
            }}
            animate={{
              y: [0, -100, 0],
              opacity: [0, 1, 0],
            }}
            transition={{
              duration: Math.random() * 3 + 2,
              repeat: Infinity,
              delay: Math.random() * 2,
            }}
          />
        ))}
      </div>

      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="glass border-b border-cyan-500/20 backdrop-blur-xl"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3, duration: 0.8 }}
              className="flex items-center"
            >
              <div className="flex items-center space-x-4">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
                  className="w-12 h-12 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-xl flex items-center justify-center neon-cyan"
                >
                  <Zap className="w-6 h-6 text-white" />
                </motion.div>
                <div>
                  <h1 className="text-3xl font-bold holographic">
                    WESEE
                  </h1>
                  <p className="text-sm text-gray-400 font-mono">
                    Advanced Media Extraction System
                  </p>
                </div>
              </div>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5, duration: 0.8 }}
              className="flex items-center space-x-6"
            >
              <div className="text-right">
                <div className="text-sm text-cyan-400 font-mono">STATUS</div>
                <div className="text-green-400 font-semibold">ONLINE</div>
              </div>
              <div className="w-3 h-3 bg-green-400 rounded-full pulse-glow"></div>
            </motion.div>
          </div>
        </div>
      </motion.header>

      {/* Navigation */}
      <motion.nav
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.8 }}
        className="glass border-b border-cyan-500/20 backdrop-blur-xl"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-2">
            {tabs.map((tab, index) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <motion.button
                  key={tab.id}
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.8 + index * 0.1, duration: 0.5 }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative flex items-center gap-3 py-4 px-6 rounded-xl font-semibold text-sm transition-all duration-300 ${
                    isActive
                      ? `bg-gradient-to-r ${tab.color} text-white shadow-lg`
                      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                  }`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 rounded-xl"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                  <Icon className={`h-5 w-5 relative z-10 ${isActive ? 'text-white' : ''}`} />
                  <span className="relative z-10">{tab.label}</span>
                  {isActive && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="w-2 h-2 bg-white rounded-full relative z-10"
                    />
                  )}
                </motion.button>
              );
            })}
          </div>
        </div>
      </motion.nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 relative z-10">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
          >
            {renderContent()}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Footer */}
      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1, duration: 0.8 }}
        className="glass border-t border-cyan-500/20 backdrop-blur-xl mt-16"
      >
        <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.2, duration: 0.8 }}
              className="text-2xl font-bold holographic mb-4"
            >
              WESEE - QUANTUM SCRAPER
            </motion.div>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.4, duration: 0.8 }}
              className="text-gray-400 mb-2"
            >
              Advanced AI-Powered Media Extraction Platform
            </motion.p>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.6, duration: 0.8 }}
              className="text-sm text-gray-500 font-mono"
            >
              Supports: YouTube • Twitter • Facebook • Reddit • Google Search • PDF Extraction
            </motion.p>
          </div>
        </div>
      </motion.footer>
    </div>
  );
};

export default App;
