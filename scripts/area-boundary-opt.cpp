// Exact-integer acceleration for the Python vertex-relocation / 2-opt search.
#include <boost/multiprecision/cpp_int.hpp>
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <numeric>
#include <utility>
#include <vector>
using Big = boost::multiprecision::cpp_int;
using Edge = std::pair<int,int>;
struct Move { Big delta; int i,j; };
int n;
std::vector<std::array<Big,2>> p;
std::vector<std::vector<Big>> cross;
std::vector<int8_t> orientation;
int at(int a,int b,int c){return orientation[(a*n+b)*n+c];}
bool on(int a,int b,int q){return std::min(p[a][0],p[b][0])<=p[q][0] && p[q][0]<=std::max(p[a][0],p[b][0]) && std::min(p[a][1],p[b][1])<=p[q][1] && p[q][1]<=std::max(p[a][1],p[b][1]);}
bool conflict(int a,int b,int c,int d){
 int shared=-1;
 if(a==c||a==d)shared=a;
 if(b==c||b==d){if(shared!=-1)return true;shared=b;}
 if(shared!=-1){int u=a==shared?b:a,v=c==shared?d:c;if(at(shared,u,v)!=0)return false;Big dot=(p[u][0]-p[shared][0])*(p[v][0]-p[shared][0])+(p[u][1]-p[shared][1])*(p[v][1]-p[shared][1]);return dot>0;}
 int x=at(a,b,c),y=at(a,b,d),z=at(c,d,a),w=at(c,d,b);
 if(x*y<0&&z*w<0)return true;
 return (x==0&&on(a,b,c))||(y==0&&on(a,b,d))||(z==0&&on(c,d,a))||(w==0&&on(c,d,b));
}
std::vector<Edge> edges;
std::vector<int> edge_id;
std::vector<std::vector<uint64_t>> conflicts;
const std::vector<uint64_t>& conflict_bits(int id){
 auto &bits=conflicts[id];
 if(!bits.empty())return bits;
 bits.resize((edges.size()+63)/64);
 auto [a,b]=edges[id];
 for(size_t k=0;k<edges.size();k++){
  if(int(k)==id)continue;
  bool hit;
  if(!conflicts[k].empty())hit=(conflicts[k][id/64]>>(id%64))&1;
  else {auto [c,d]=edges[k];hit=conflict(a,b,c,d);}
  if(hit)bits[k/64]|=uint64_t(1)<<(k%64);
 }
 return bits;
}
bool valid_changes(const std::vector<int>& order,const std::vector<Edge>& changed){
 std::vector<uint64_t> active((edges.size()+63)/64);
 for(int k=0;k<n;k++){int id=edge_id[order[k]*n+order[(k+1)%n]];active[id/64]|=uint64_t(1)<<(id%64);}
 for(auto [a,b]:changed){const auto &bits=conflict_bits(edge_id[a*n+b]);for(size_t k=0;k<bits.size();k++)if(bits[k]&active[k])return false;}
 return true;
}
Big area(const std::vector<int>& o){Big r=0;for(int k=0;k<n;k++)r+=cross[o[k]][o[(k+1)%n]];return r;}
void sort_moves(std::vector<Move>& v){std::sort(v.begin(),v.end(),[](const Move&a,const Move&b){if(a.delta!=b.delta)return a.delta<b.delta;if(a.i!=b.i)return a.i<b.i;return a.j<b.j;});}
std::pair<std::vector<int>,long long> improve(std::vector<int> order){
 long long moves=0;
 while(true){
  Big current=area(order);std::vector<Move> proposals;
  for(int i=0;i<n;i++){int v=order[i],a=order[(i+n-1)%n],b=order[(i+1)%n];Big remove=cross[a][b]-cross[a][v]-cross[v][b];
   for(int j=0;j<n;j++){int c=order[j],d=order[(j+1)%n];if(v==c||v==d)continue;Big delta=remove+cross[c][v]+cross[v][d]-cross[c][d];if(delta<0&&delta>-current)proposals.push_back({delta,i,j});}}
  sort_moves(proposals);bool moved=false;
  for(const auto & m:proposals){int i=m.i,j=m.j,v=order[i],c=order[j],a=order[(i+n-1)%n],b=order[(i+1)%n],d=order[(j+1)%n];std::vector<int> candidate=order;candidate.erase(candidate.begin()+i);auto pos=std::find(candidate.begin(),candidate.end(),c);candidate.insert(pos+1,v);
   if(valid_changes(candidate,{{a,b},{c,v},{v,d}})){order=std::move(candidate);moves++;moved=true;break;}}
  if(moved)continue;
  std::vector<Big> prefix(n);for(int k=0;k<n-1;k++)prefix[k+1]=prefix[k]+cross[order[k]][order[k+1]];
  proposals.clear();for(int i=0;i<n;i++){int a=order[i],b=order[(i+1)%n];for(int j=i+2;j<n;j++){if(i==0&&j==n-1)continue;int c=order[j],d=order[(j+1)%n];Big delta=cross[a][c]+cross[b][d]-cross[a][b]-cross[c][d]-2*(prefix[j]-prefix[i+1]);if(delta<0&&delta>-current)proposals.push_back({delta,i,j});}}
  sort_moves(proposals);for(const auto &m:proposals){int i=m.i,j=m.j;std::vector<int> candidate=order;std::reverse(candidate.begin()+i+1,candidate.begin()+j+1);int a=order[i],b=order[i+1],c=order[j],d=order[(j+1)%n];if(valid_changes(candidate,{{a,c},{b,d}})){order=std::move(candidate);moves++;moved=true;break;}}
  if(!moved)return {order,moves};
 }
}
int main(){
 int seeds;if(!(std::cin>>n>>seeds)||n<3||seeds<1)return 2;
 p.resize(n);for(auto &v:p)std::cin>>v[0]>>v[1];
 cross.assign(n,std::vector<Big>(n));for(int a=0;a<n;a++)for(int b=0;b<n;b++)cross[a][b]=p[a][0]*p[b][1]-p[a][1]*p[b][0];
 orientation.resize(n*n*n);for(int a=0;a<n;a++)for(int b=a+1;b<n;b++)for(int c=b+1;c<n;c++){Big t=cross[a][b]+cross[b][c]+cross[c][a];int s=(t>0)-(t<0);orientation[(a*n+b)*n+c]=s;orientation[(b*n+c)*n+a]=s;orientation[(c*n+a)*n+b]=s;orientation[(a*n+c)*n+b]=-s;orientation[(c*n+b)*n+a]=-s;orientation[(b*n+a)*n+c]=-s;}
 edge_id.resize(n*n,-1);for(int a=0;a<n;a++)for(int b=a+1;b<n;b++){edge_id[a*n+b]=edge_id[b*n+a]=edges.size();edges.emplace_back(a,b);}conflicts.resize(edges.size());
 std::vector<int> best;Big best_area;long long total_moves=0;
 for(int s=0;s<seeds;s++){std::vector<int> order(n);for(int &i:order)std::cin>>i;auto result=improve(order);Big found=area(result.first);total_moves+=result.second;if(best.empty()||found<best_area){best=result.first;best_area=found;}}
 std::cout<<total_moves<<'\n';for(int i:best)std::cout<<i<<' ';std::cout<<'\n';return 0;
}
