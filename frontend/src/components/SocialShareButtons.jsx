import React from 'react';
import { Facebook, Twitter, Linkedin, Mail, Link2 } from 'lucide-react';

/**
 * Social Share Buttons Component
 * Adds share functionality for products and blog posts
 */
const SocialShareButtons = ({ url, title, description, className = '' }) => {
  const encodedUrl = encodeURIComponent(url || window.location.href);
  const encodedTitle = encodeURIComponent(title || document.title);
  const encodedDescription = encodeURIComponent(description || '');

  const shareLinks = [
    {
      name: 'Facebook',
      icon: Facebook,
      url: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
      color: 'hover:bg-blue-600 hover:text-white',
      bgColor: 'bg-blue-50 text-blue-600'
    },
    {
      name: 'Twitter',
      icon: Twitter,
      url: `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`,
      color: 'hover:bg-sky-500 hover:text-white',
      bgColor: 'bg-sky-50 text-sky-500'
    },
    {
      name: 'LinkedIn',
      icon: Linkedin,
      url: `https://www.linkedin.com/shareArticle?mini=true&url=${encodedUrl}&title=${encodedTitle}&summary=${encodedDescription}`,
      color: 'hover:bg-blue-700 hover:text-white',
      bgColor: 'bg-blue-50 text-blue-700'
    },
    {
      name: 'Email',
      icon: Mail,
      url: `mailto:?subject=${encodedTitle}&body=${encodedDescription}%0A%0A${encodedUrl}`,
      color: 'hover:bg-gray-700 hover:text-white',
      bgColor: 'bg-gray-100 text-gray-700'
    },
    {
      name: 'WhatsApp',
      icon: () => (
        <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
        </svg>
      ),
      url: `https://wa.me/?text=${encodedTitle}%20${encodedUrl}`,
      color: 'hover:bg-green-500 hover:text-white',
      bgColor: 'bg-green-50 text-green-600'
    }
  ];

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(url || window.location.href);
      // You could add a toast notification here
      alert('Link gekopieerd!');
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleShare = (shareUrl, name) => {
    // Track share event
    if (window.gtag) {
      window.gtag('event', 'share', {
        method: name,
        content_type: 'product',
        item_id: url
      });
    }
    
    window.open(shareUrl, '_blank', 'noopener,noreferrer,width=600,height=400');
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className="text-sm text-gray-500 mr-1">Delen:</span>
      {shareLinks.map((link) => (
        <button
          key={link.name}
          onClick={() => handleShare(link.url, link.name)}
          className={`w-9 h-9 rounded-full ${link.bgColor} ${link.color} flex items-center justify-center transition-all duration-200`}
          title={`Deel via ${link.name}`}
          aria-label={`Deel via ${link.name}`}
        >
          <link.icon className="w-4 h-4" />
        </button>
      ))}
      <button
        onClick={copyToClipboard}
        className="w-9 h-9 rounded-full bg-gray-100 text-gray-600 hover:bg-gray-700 hover:text-white flex items-center justify-center transition-all duration-200"
        title="Kopieer link"
        aria-label="Kopieer link"
      >
        <Link2 className="w-4 h-4" />
      </button>
    </div>
  );
};

export default SocialShareButtons;
