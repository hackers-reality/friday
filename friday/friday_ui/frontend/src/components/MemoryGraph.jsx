import React, { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';

export default function MemoryGraph({ data, entities }) {
  const svgRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (!data || !svgRef.current) return;

    const container = svgRef.current.parentElement;
    if (container) {
      setDimensions({
        width: container.clientWidth || 800,
        height: container.clientHeight || 600,
      });
    }
  }, [data]);

  useEffect(() => {
    if (!data || !svgRef.current) return;

    const { width, height } = dimensions;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const nodes = (data.nodes || []).map(d => ({ ...d }));
    const edges = (data.edges || []).map(d => ({ ...d }));

    if (nodes.length === 0) {
      svg.append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', '#4a9eff')
        .attr('font-size', '14px')
        .text('No memory data yet. Start chatting to build the knowledge graph.');
      return;
    }

    const g = svg.append('g');

    const zoom = d3.zoom()
      .scaleExtent([0.3, 4])
      .on('zoom', (event) => g.attr('transform', event.transform));
    svg.call(zoom);

    const colorMap = {
      person: '#ff6b6b',
      organization: '#4ecdc4',
      location: '#45b7d1',
      concept: '#96ceb4',
      acronym: '#ffeaa7',
      technology: '#a29bfe',
      unknown: '#636e72',
    };

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(edges).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d => d.size || 10));

    const link = g.append('g')
      .selectAll('line')
      .data(edges)
      .enter()
      .append('line')
      .attr('stroke', '#1a3a5c')
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.6);

    const node = g.append('g')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }));

    node.append('circle')
      .attr('r', d => d.size || 8)
      .attr('fill', d => colorMap[d.type] || colorMap.unknown)
      .attr('stroke', '#0a1628')
      .attr('stroke-width', 2)
      .attr('cursor', 'pointer')
      .on('mouseover', function(event, d) {
        d3.select(this).attr('stroke', '#00d4ff').attr('stroke-width', 3);
      })
      .on('mouseout', function(event, d) {
        d3.select(this).attr('stroke', '#0a1628').attr('stroke-width', 2);
      })
      .on('click', (event, d) => {
        setSelectedNode(d);
      });

    node.append('text')
      .text(d => d.id?.length > 15 ? d.id.slice(0, 15) + '...' : d.id)
      .attr('x', d => (d.size || 8) + 4)
      .attr('y', 4)
      .attr('fill', '#8ec8e8')
      .attr('font-size', '10px')
      .attr('font-family', 'Share Tech Mono, monospace');

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, [data, dimensions]);

  const typeColors = {
    person: '#ff6b6b',
    organization: '#4ecdc4',
    location: '#45b7d1',
    concept: '#96ceb4',
    acronym: '#ffeaa7',
    technology: '#a29bfe',
    unknown: '#636e72',
  };

  return (
    <div className="memory-graph-container">
      <div className="graph-header">
        <div className="graph-title">KNOWLEDGE GRAPH</div>
        <div className="graph-stats">
          <span>{data?.nodes?.length || 0} nodes</span>
          <span>{data?.edges?.length || 0} edges</span>
        </div>
        <div className="graph-legend">
          {Object.entries(typeColors).map(([type, color]) => (
            <div key={type} className="legend-item">
              <span className="legend-dot" style={{ background: color }} />
              <span>{type}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="graph-canvas">
        <svg
          ref={svgRef}
          width={dimensions.width}
          height={dimensions.height}
          style={{ background: 'transparent' }}
        />
      </div>

      {selectedNode && (
        <div className="graph-node-info">
          <div className="node-info-header">
            <span className="node-name">{selectedNode.id}</span>
            <button className="node-close" onClick={() => setSelectedNode(null)}>×</button>
          </div>
          <div className="node-info-body">
            <div className="node-detail"><span>Type:</span> {selectedNode.type}</div>
            <div className="node-detail"><span>Mentions:</span> {selectedNode.mentions}</div>
            <div className="node-detail"><span>Size:</span> {selectedNode.size}</div>
          </div>
        </div>
      )}
    </div>
  );
}
