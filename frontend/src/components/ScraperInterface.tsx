import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Link, Search, X, Plus, Zap, Sparkles, Cpu, Database } from 'lucide-react';
import { apiService, ScrapeRequest } from '../services/api';

interface ScraperInterfaceProps {
  onScrapeStart: () => void;
}

const ScraperInterface: React.FC<ScraperInterfaceProps> = ({ onScrapeStart }) => {
  const [urls, setUrls] = useState<string[]>(['']);
  const [keywords, setKeywords] = useState<string[]>(['']);
  const [loading, setLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [activeSection, setActiveSection] = useState<'urls' | 'keywords'>('urls');

  const addUrl = () => {
    setUrls([...urls, '']);
  };

  const removeUrl = (index: number) => {
    if (urls.length > 1) {
      setUrls(urls.filter((_, i) => i !== index));
    }
  };

  const updateUrl = (index: number, value: string) => {
    const newUrls = [...urls];
    newUrls[index] = value;
    setUrls(newUrls);
  };

  const addKeyword = () => {
    setKeywords([...keywords, '']);
  };

  const removeKeyword = (index: number) => {
    if (keywords.length > 1) {
      setKeywords(keywords.filter((_, i) => i !== index));
    }
  };

  const updateKeyword = (index: number, value: string) => {
    const newKeywords = [...keywords];
    newKeywords[index] = value;
    setKeywords(newKeywords);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const validUrls = urls.filter(url => url.trim());
    const validKeywords = keywords.filter(keyword => keyword.trim());

    if (validUrls.length === 0 && validKeywords.length === 0) {
      alert('Please enter at least one URL or keyword');
      return;
    }

    try {
      setLoading(true);
      onScrapeStart();
      
      const request: ScrapeRequest = {
        urls: validUrls,
        keywords: validKeywords,
      };

      await apiService.scrapeContent(request);
      setShowSuccess(true);
      
      // Reset form
      setUrls(['']);
      setKeywords(['']);
    } catch (error) {
      console.error('Failed to start scraping:', error);
      alert('Failed to start scraping. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative">
      {/* Animated Background Grid */}
      <div className="absolute inset-0 opacity-10">
        <div className="grid grid-cols-12 gap-4 h-full">
          {[...Array(48)].map((_, i) => (
            <motion.div
              key={i}
              className="border border-cyan-500/20 rounded"
              animate={{
                opacity: [0.1, 0.3, 0.1],
              }}
              transition={{
                duration: 2 + Math.random() * 2,
                repeat: Infinity,
                delay: Math.random() * 2,
              }}
            />
          ))}
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="card p-8 relative z-10"
      >
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.8 }}
          className="text-center mb-8"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            className="w-16 h-16 mx-auto mb-4 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-2xl flex items-center justify-center neon-cyan"
          >
            <Zap className="w-8 h-8 text-white" />
          </motion.div>
          <h2 className="text-4xl font-bold holographic mb-2">QUANTUM SCRAPER</h2>
          <p className="text-gray-400 text-lg">Advanced AI-Powered Media Extraction</p>
        </motion.div>

        {/* Success Modal */}
        <AnimatePresence>
          {showSuccess && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50"
            >
              <motion.div
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.5, opacity: 0 }}
                className="card p-8 max-w-md w-full mx-4 text-center"
              >
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: "spring", bounce: 0.6 }}
                  className="w-20 h-20 mx-auto mb-6 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full flex items-center justify-center neon-pink"
                >
                  <Sparkles className="w-10 h-10 text-white" />
                </motion.div>
                <h3 className="text-2xl font-bold text-white mb-4">Mission Initiated!</h3>
                <p className="text-gray-300 mb-6">
                  Quantum scraper is now processing your request. Check the <strong className="text-cyan-400">Neural Videos</strong> and <strong className="text-cyan-400">Holographic PDFs</strong> tabs for results.
                </p>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setShowSuccess(false)}
                  className="btn btn-success w-full"
                >
                  Acknowledged
                </motion.button>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Section Toggle */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.8 }}
            className="flex space-x-2 p-1 bg-gray-800/50 rounded-xl"
          >
            <motion.button
              type="button"
              onClick={() => setActiveSection('urls')}
              className={`flex-1 py-3 px-4 rounded-lg font-semibold transition-all duration-300 ${
                activeSection === 'urls'
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg'
                  : 'text-gray-400 hover:text-white'
              }`}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Link className="inline w-4 h-4 mr-2" />
              URL Extraction
            </motion.button>
            <motion.button
              type="button"
              onClick={() => setActiveSection('keywords')}
              className={`flex-1 py-3 px-4 rounded-lg font-semibold transition-all duration-300 ${
                activeSection === 'keywords'
                  ? 'bg-gradient-to-r from-purple-500 to-pink-600 text-white shadow-lg'
                  : 'text-gray-400 hover:text-white'
              }`}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Search className="inline w-4 h-4 mr-2" />
              AI Search
            </motion.button>
          </motion.div>

          {/* URLs Section */}
          <AnimatePresence mode="wait">
            {activeSection === 'urls' && (
              <motion.div
                key="urls"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.5 }}
                className="space-y-6"
              >
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center">
                    <Link className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white">URL Extraction Matrix</h3>
                    <p className="text-gray-400 text-sm">Enter target URLs for media extraction</p>
                  </div>
                </div>

                <div className="space-y-4">
                  {urls.map((url, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="flex gap-3"
                    >
                      <div className="flex-1 relative">
                        <input
                          type="url"
                          value={url}
                          onChange={(e) => updateUrl(index, e.target.value)}
                          placeholder="https://example.com"
                          className="input pr-12"
                        />
                        <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                          <Cpu className="w-4 h-4 text-cyan-400" />
                        </div>
                      </div>
                      {urls.length > 1 && (
                        <motion.button
                          type="button"
                          onClick={() => removeUrl(index)}
                          className="p-3 text-red-400 hover:text-red-300 hover:bg-red-500/20 rounded-lg transition-all duration-300"
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                        >
                          <X className="h-5 w-5" />
                        </motion.button>
                      )}
                    </motion.div>
                  ))}
                </div>

                <motion.button
                  type="button"
                  onClick={addUrl}
                  className="flex items-center gap-2 text-cyan-400 hover:text-cyan-300 text-sm font-semibold transition-colors duration-300"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Plus className="h-4 w-4" />
                  Add URL Matrix
                </motion.button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Keywords Section */}
          <AnimatePresence mode="wait">
            {activeSection === 'keywords' && (
              <motion.div
                key="keywords"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.5 }}
                className="space-y-6"
              >
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-pink-600 rounded-lg flex items-center justify-center">
                    <Search className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white">AI Search Parameters</h3>
                    <p className="text-gray-400 text-sm">Define search terms for intelligent PDF discovery</p>
                  </div>
                </div>

                <div className="space-y-4">
                  {keywords.map((keyword, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="flex gap-3"
                    >
                      <div className="flex-1 relative">
                        <input
                          type="text"
                          value={keyword}
                          onChange={(e) => updateKeyword(index, e.target.value)}
                          placeholder="artificial intelligence"
                          className="input pr-12"
                        />
                        <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                          <Database className="w-4 h-4 text-purple-400" />
                        </div>
                      </div>
                      {keywords.length > 1 && (
                        <motion.button
                          type="button"
                          onClick={() => removeKeyword(index)}
                          className="p-3 text-red-400 hover:text-red-300 hover:bg-red-500/20 rounded-lg transition-all duration-300"
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                        >
                          <X className="h-5 w-5" />
                        </motion.button>
                      )}
                    </motion.div>
                  ))}
                </div>

                <motion.button
                  type="button"
                  onClick={addKeyword}
                  className="flex items-center gap-2 text-purple-400 hover:text-purple-300 text-sm font-semibold transition-colors duration-300"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Plus className="h-4 w-4" />
                  Add Search Parameter
                </motion.button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Platform Info */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.8 }}
            className="glass rounded-2xl p-6 border border-cyan-500/20"
          >
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-cyan-400" />
              Supported Platforms
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-cyan-400 font-semibold mb-2">Video Sources:</p>
                <p className="text-gray-300">YouTube • Twitter • Facebook • Reddit • Coursera • IBM</p>
              </div>
              <div>
                <p className="text-purple-400 font-semibold mb-2">PDF Sources:</p>
                <p className="text-gray-300">Google Search • Direct URLs • Website Crawling</p>
              </div>
            </div>
            <div className="mt-4 p-3 bg-gradient-to-r from-cyan-500/10 to-purple-500/10 rounded-lg border border-cyan-500/20">
              <p className="text-sm text-gray-300">
                <strong className="text-cyan-400">Note:</strong> Processing runs in quantum background. Monitor progress in other tabs.
              </p>
            </div>
          </motion.div>

          {/* Submit Button */}
          <motion.button
            type="submit"
            disabled={loading}
            className="btn btn-primary w-full flex items-center justify-center gap-3 py-4 text-lg font-bold relative overflow-hidden"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.8 }}
          >
            {loading ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full"
                />
                Initializing Quantum Scraper...
              </>
            ) : (
              <>
                <Zap className="w-6 h-6" />
                Launch Quantum Extraction
              </>
            )}
          </motion.button>
        </form>
      </motion.div>
    </div>
  );
};

export default ScraperInterface;
