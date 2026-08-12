 /*
 * Copyright (c) 2002
 * John Maddock
 *
 * Use, modification and distribution are subject to the 
 * Boost Software License, Version 1.0. (See accompanying file 
 * LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
 *
 */

 /*
  *   LOCATION:    see http://www.boost.org for most recent version.
  *   FILE         mem_block_cache.hpp
  *   VERSION      see <boost/version.hpp>
  *   DESCRIPTION: memory block cache used by the non-recursive matcher.
  */

#ifndef BOOST_REGEX_V5_MEM_BLOCK_CACHE_HPP
#define BOOST_REGEX_V5_MEM_BLOCK_CACHE_HPP

#include <boost/regex/config.hpp>
#ifndef BOOST_REGEX_AS_MODULE
#include <new>
#ifdef BOOST_HAS_THREADS
#include <mutex>
#endif

#ifndef BOOST_NO_CXX11_HDR_ATOMIC
  #include <atomic>
  #if ATOMIC_POINTER_LOCK_FREE == 2
    #define BOOST_REGEX_MEM_BLOCK_CACHE_LOCK_FREE
    #define BOOST_REGEX_ATOMIC_POINTER std::atomic
  #endif
#endif
#endif


namespace boost{
namespace BOOST_REGEX_DETAIL_NS{

#if BOOST_REGEX_MAX_CACHE_BLOCKS != 0
#ifdef BOOST_REGEX_MEM_BLOCK_CACHE_LOCK_FREE /* lock free implementation */
struct mem_block_cache
{
  std::atomic<void*> cache[BOOST_REGEX_MAX_CACHE_BLOCKS];

   ~mem_block_cache()
   {
     for (size_t i = 0;i < BOOST_REGEX_MAX_CACHE_BLOCKS; ++i) {
       if (cache[i].load()) ::operator delete(cache[i].load());
     }
   }
   void* get()
   {
     for (size_t i = 0;i < BOOST_REGEX_MAX_CACHE_BLOCKS; ++i) {
       void* p = cache[i].load();
       if (p != NULL) {
         if (cache[i].compare_exchange_strong(p, NULL)) return p;
       }
     }
     return ::operator new(BOOST_REGEX_BLOCKSIZE);
   }
   void put(void* ptr)
   {
     for (size_t i = 0;i < BOOST_REGEX_MAX_CACHE_BLOCKS; ++i) {
       void* p = cache[i].load();
       if (p == NULL) {
         if (cache[i].compare_exchange_strong(p, ptr)) return;
       }
     }
     ::operator delete(ptr);
   }

   static mem_block_cache& instance();
};

// boost-module (M5 B'): 原为 instance() 函数内 static — gcc 模块管线在消费者 TU 以强符号
// 发射函数内 static (非 COMDAT), 与 regex 库 TU 定义多重定义; 改命名空间作用域内部链接
// 对象, 每 TU 独立持有 (纯缓存, 语义等价)。instance() 定义移出类 (类内体看不到其后声明)。
static mem_block_cache block_cache = { { {nullptr} } };

inline mem_block_cache& mem_block_cache::instance()
{
   return block_cache;
}


#else /* lock-based implementation */


struct mem_block_node
{
   mem_block_node* next;
};

struct mem_block_cache
{
   // this member has to be statically initialsed:
   mem_block_node* next { nullptr };
   unsigned cached_blocks { 0 };
#ifdef BOOST_HAS_THREADS
   std::mutex mut;
#endif

   ~mem_block_cache()
   {
      while(next)
      {
         mem_block_node* old = next;
         next = next->next;
         ::operator delete(old);
      }
   }
   void* get()
   {
#ifdef BOOST_HAS_THREADS
      std::lock_guard<std::mutex> g(mut);
#endif
     if(next)
      {
         mem_block_node* result = next;
         next = next->next;
         --cached_blocks;
         return result;
      }
      return ::operator new(BOOST_REGEX_BLOCKSIZE);
   }
   void put(void* p)
   {
#ifdef BOOST_HAS_THREADS
      std::lock_guard<std::mutex> g(mut);
#endif
      if(cached_blocks >= BOOST_REGEX_MAX_CACHE_BLOCKS)
      {
         ::operator delete(p);
      }
      else
      {
         mem_block_node* old = static_cast<mem_block_node*>(p);
         old->next = next;
         next = old;
         ++cached_blocks;
      }
   }
   static mem_block_cache& instance();
};

// boost-module (M5 B'): 同 lock-free 版本注释 (见上), 每 TU 独立持有。
static mem_block_cache block_cache;

inline mem_block_cache& mem_block_cache::instance()
{
   return block_cache;
}
#endif
#endif

#if BOOST_REGEX_MAX_CACHE_BLOCKS == 0

inline void*  get_mem_block()
{
   return ::operator new(BOOST_REGEX_BLOCKSIZE);
}

inline void  put_mem_block(void* p)
{
   ::operator delete(p);
}

#else

inline void*  get_mem_block()
{
   return mem_block_cache::instance().get();
}

inline void  put_mem_block(void* p)
{
   mem_block_cache::instance().put(p);
}

#endif
}
} // namespace boost

#endif

