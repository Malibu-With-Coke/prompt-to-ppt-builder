import { Link, useLocation } from 'react-router-dom';

export default function Header() {
  const location = useLocation();

  const getLinkClasses = (path: string) => {
    const isActive = location.pathname.startsWith(path);
    return isActive
      ? "text-[#001F3F] dark:text-white font-bold border-b-2 border-[#001F3F] dark:border-white pb-1"
      : "text-slate-500 dark:text-slate-400 hover:text-[#001F3F] dark:hover:text-white duration-200 ease-in-out transition-colors font-medium";
  };

  return (
    <header className="bg-slate-50/80 backdrop-blur-md dark:bg-[#000613]/80 sticky top-0 z-50 flex justify-between items-center w-full px-8 py-4 text-[#001F3F] dark:text-white font-headline text-sm tracking-tight border-b border-outline-variant/10 shadow-sm">
      <div className="flex items-center gap-8 max-w-[1920px] mx-auto w-full">
        <Link to="/" className="text-2xl font-bold tracking-tighter text-[#001F3F] dark:text-white">
          ArchitectEditor
        </Link>
        <div className="flex gap-6 mt-1 ml-4 sm:ml-8 font-body">
          <Link to="/upload" className={getLinkClasses("/upload")}>Projects</Link>
          <Link to="#" className="text-slate-500 font-medium hover:text-[#001f3f] dark:hover:text-white transition-colors">Templates</Link>
          <Link to="/history" className={getLinkClasses("/history")}>History</Link>
          <Link to="#" className="text-slate-500 font-medium hover:text-[#001f3f] dark:hover:text-white transition-colors">Archive</Link>
        </div>
        
        <div className="flex items-center gap-4 ml-auto">
          <button className="p-2 rounded-full hover:bg-slate-200/50 dark:hover:bg-[#001F3F]/50 transition-colors text-slate-500">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button className="p-2 rounded-full hover:bg-slate-200/50 dark:hover:bg-[#001F3F]/50 transition-colors text-slate-500">
            <span className="material-symbols-outlined">settings</span>
          </button>
          
          <Link to="/upload" className="hidden sm:flex btn-gradient text-white px-5 py-2 rounded-md font-semibold text-sm transition-transform active:scale-95 ml-2">
            New Deck
          </Link>
          
          <div className="w-9 h-9 rounded-full overflow-hidden ml-2 ring-2 ring-primary-fixed bg-surface-container-highest">
            <img 
              alt="User profile" 
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDD_M6caIOfz4CbNSLBqlROwqCcdRmYcfTZUrZmDglvF4qzqF1_RLgtEe8bkzBYZFQpApdDf1T-3AYRVzPAcu9Y68zWDk2Y2aKeztvZm-jdgBUEWvA-L1Vge4gnoRn0OXzayx6tynP3jISzIWfFPgLy-CJNgNjmbo2UQkXmnhujA2UPPz2RbmIFNhjLZW3ZCF9rEIFt8KHemhooKbNKUvbOYzx1nSP_gV5dRgrFiyH2nQvmmUpurVUhGQLSWYx3IneTBInZEYUnKlo" 
              className="w-full h-full object-cover" 
            />
          </div>
        </div>
      </div>
    </header>
  );
}
